// API Communication Module

const API = {
    // System Status
    async getSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            return await response.json();
        } catch (error) {
            console.error('Error fetching system status:', error);
            return null;
        }
    },

    // System Performance
    async getSystemPerformance() {
        try {
            const response = await fetch('/api/system/performance');
            return await response.json();
        } catch (error) {
            console.error('Error fetching system performance:', error);
            return null;
        }
    },

    // System Alerts
    async getSystemAlerts() {
        try {
            const response = await fetch('/api/system/alerts');
            return await response.json();
        } catch (error) {
            console.error('Error fetching system alerts:', error);
            return null;
        }
    },

    // Camera Analytics
    async getCameraAnalytics() {
        try {
            const response = await fetch('/api/cameras/analytics');
            return await response.json();
        } catch (error) {
            console.error('Error fetching camera analytics:', error);
            return null;
        }
    },

    // Get Cameras
    async getCameras() {
        try {
            const response = await fetch('/api/cameras');
            return await response.json();
        } catch (error) {
            console.error('Error fetching cameras:', error);
            return [];
        }
    },

    // Recording Status
    async getRecordingStatus() {
        try {
            const response = await fetch('/api/recording/status');
            return await response.json();
        } catch (error) {
            console.error('Error fetching recording status:', error);
            return {};
        }
    }
};
