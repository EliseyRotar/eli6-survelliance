// Analytics Module

const Analytics = {
    async load() {
        const data = await API.getCameraAnalytics();
        if (data) {
            this.display(data);
        }
    },

    display(data) {
        document.getElementById('avgResponseTime').textContent = `${Math.round(data.average_response_time || 0)}ms`;
        document.getElementById('avgFrameRate').textContent = `${Math.round(data.average_fps || 0)} FPS`;
        const errorRate = data.total_errors > 0 ? ((data.total_errors / data.total_cameras) * 100).toFixed(1) : '0.0';
        document.getElementById('errorRate').textContent = `${errorRate}%`;
    }
};
