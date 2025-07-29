document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/workout_data')
        .then(response => response.json())
        .then(data => {
            // Progress Chart (Weight over time)
            const progressCtx = document.getElementById('progressChart').getContext('2d');
            const progressChart = new Chart(progressCtx, {
                type: 'line',
                data: {
                    datasets: Object.keys(data).map(exercise => ({
                        label: exercise,
                        data: data[exercise].dates.map((date, i) => ({
                            x: date,
                            y: data[exercise].weights[i]
                        })),
                        borderColor: getRandomColor(),
                        backgroundColor: 'rgba(0, 0, 0, 0)',
                        tension: 0.1
                    }))
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Weight (kg/lbs)'
                            }
                        }
                    }
                }
            });

            // Exercise Breakdown Chart
            const exerciseCtx = document.getElementById('exerciseChart').getContext('2d');
            const exerciseChart = new Chart(exerciseCtx, {
                type: 'bar',
                data: {
                    labels: Object.keys(data),
                    datasets: [{
                        label: 'Total Volume (Weight × Reps)',
                        data: Object.keys(data).map(exercise => {
                            return data[exercise].weights.reduce((total, weight, i) => {
                                return total + (weight * data[exercise].reps[i]);
                            }, 0);
                        }),
                        backgroundColor: Object.keys(data).map(() => getRandomColor())
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Total Volume'
                            }
                        }
                    }
                }
            });
        });

    function getRandomColor() {
        const letters = '0123456789ABCDEF';
        let color = '#';
        for (let i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }
});