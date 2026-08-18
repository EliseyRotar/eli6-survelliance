// Chart Management Module

const Charts = {
    initialize() {
        this.initCPUChart();
        this.initMemoryChart();
        this.initNetworkChart();
        this.initCameraChart();
    },

    initCPUChart() {
        const ctx = document.getElementById('cpuChart');
        if (!ctx) return;

        STATE.charts.cpu = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage (%)',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: this.getLineChartOptions(100)
        });
    },

    initMemoryChart() {
        const ctx = document.getElementById('memoryChart');
        if (!ctx) return;

        STATE.charts.memory = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory Usage (%)',
                    data: [],
                    borderColor: '#ffa500',
                    backgroundColor: 'rgba(255, 165, 0, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: this.getLineChartOptions(100)
        });
    },

    initNetworkChart() {
        const ctx = document.getElementById('networkChart');
        if (!ctx) return;

        STATE.charts.network = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Network (MB/s)',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: this.getLineChartOptions()
        });
    },

    initCameraChart() {
        const ctx = document.getElementById('cameraChart');
        if (!ctx) return;

        STATE.charts.camera = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline', 'Unstable'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#00ff88', '#ff4757', '#ffa500'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#b8b8b8',
                            padding: 20
                        }
                    }
                }
            }
        });
    },

    getLineChartOptions(maxY = null) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: maxY,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#b8b8b8'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#b8b8b8'
                    }
                }
            }
        };
    }
};
