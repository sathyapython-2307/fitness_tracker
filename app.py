from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import csv
from io import StringIO
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['EXPORT_FOLDER'] = 'exports'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    workouts = db.relationship('Workout', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise = db.Column(db.String(100), nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text)

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class WorkoutForm(FlaskForm):
    exercise = SelectField('Exercise', choices=[
        ('Squat', 'Squat'),
        ('Bench Press', 'Bench Press'),
        ('Deadlift', 'Deadlift'),
        ('Overhead Press', 'Overhead Press'),
        ('Pull-up', 'Pull-up'),
        ('Barbell Row', 'Barbell Row'),
        ('Dumbbell Curl', 'Dumbbell Curl'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    reps = IntegerField('Reps', validators=[DataRequired()])
    weight = FloatField('Weight (kg/lbs)', validators=[DataRequired()])
    notes = StringField('Notes')
    submit = SubmitField('Log Workout')

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/log_workout', methods=['GET', 'POST'])
@login_required
def log_workout():
    form = WorkoutForm()
    if form.validate_on_submit():
        workout = Workout(
            user_id=current_user.id,
            exercise=form.exercise.data,
            reps=form.reps.data,
            weight=form.weight.data,
            notes=form.notes.data
        )
        db.session.add(workout)
        db.session.commit()
        flash('Workout logged successfully!')
        return redirect(url_for('workout_history'))
    return render_template('log_workout.html', form=form)

@app.route('/workout_history')
@login_required
def workout_history():
    workouts = Workout.query.filter_by(user_id=current_user.id).order_by(Workout.date.desc()).all()
    return render_template('workout_history.html', workouts=workouts)

@app.route('/progress')
@login_required
def progress():
    return render_template('progress.html')

@app.route('/api/workout_data')
@login_required
def workout_data():
    workouts = Workout.query.filter_by(user_id=current_user.id).order_by(Workout.date).all()
    
    # Group by exercise and date
    data = {}
    for workout in workouts:
        if workout.exercise not in data:
            data[workout.exercise] = {'dates': [], 'weights': [], 'reps': []}
        
        data[workout.exercise]['dates'].append(workout.date.strftime('%Y-%m-%d'))
        data[workout.exercise]['weights'].append(workout.weight)
        data[workout.exercise]['reps'].append(workout.reps)
    
    return jsonify(data)

@app.route('/export_csv')
@login_required
def export_csv():
    workouts = Workout.query.filter_by(user_id=current_user.id).order_by(Workout.date).all()
    
    # Create CSV in memory
    si = StringIO()
    cw = csv.writer(si)
    
    # Write header
    cw.writerow(['Date', 'Exercise', 'Reps', 'Weight (kg/lbs)', 'Notes'])
    
    # Write data
    for workout in workouts:
        cw.writerow([
            workout.date.strftime('%Y-%m-%d'),
            workout.exercise,
            workout.reps,
            workout.weight,
            workout.notes or ''
        ])
    
    # Save to file
    filename = f"workouts_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.csv"
    filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
    
    with open(filepath, 'w', newline='') as f:
        f.write(si.getvalue())
    
    return send_from_directory(
        app.config['EXPORT_FOLDER'],
        filename,
        as_attachment=True,
        mimetype='text/csv'
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not os.path.exists(app.config['EXPORT_FOLDER']):
            os.makedirs(app.config['EXPORT_FOLDER'])
    app.run(debug=True)