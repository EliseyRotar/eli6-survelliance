// Dashboard Module

const Dashboard = {
    async update() {
        const systemData = await API.getSystemStatus();
        if (!systemData) {
            UI.updateSystemStatus('offline');
            return;
        }

        STATE.systemData = systemData;
        this.updateDisplay();
        this.updateCharts();
    },

    updateDisplay() {
        if (!STATE.systemData.system) return;

        const sys = STATE.systemData.system;
        const totalCameras = STATE.cameras.length || CONFIG.TOTAL_CAMERAS;
        
        // Update header status
        this.updateElement('activeCameras', `${sys.active_cameras}/${totalCameras}`);
        this.updateElement('cpuUsage', `${Math.round(sys.cpu_current)}%`);
        this.updateElement('diskUsage', `${Math.round(sys.disk_current || 0)}%`);
        
        if (sys.temperature !== undefined && sys.temperature !== null) {
            this.updateElement('temperature', `${Math.round(sys.temperature)}°C`);
        }

        // Update dashboard cards
        this.updateElement('totalCameras', totalCameras);
        this.updateElement('onlineCameras', sys.active_cameras);
        this.updateElement('activeRecordings', Object.keys(STATE.systemData.recordings || {}).length);
        
        // Calculate camera type counts
        let videoCameras = 0;
        let imageCameras = 0;
        STATE.cameras.forEach(camera => {
            if (camera.type === 'video') videoCameras++;
            else imageCameras++;
        });
        this.updateElement('videoCameras', videoCameras);
        this.updateElement('imageCameras', imageCameras);
        
        // Calculate success rate
        const successRate = sys.active_cameras > 0 ? Math.round((sys.active_cameras / totalCameras) * 100) : 0;
        this.updateElement('onlinePercentage', `${successRate}%`);
        
        // Format uptime
        this.updateElement('systemUptime', UI.formatUptime(sys.uptime));

        // Update system info panel
        this.updateElement('totalThreads', STATE.systemData.active_threads || totalCameras);
        this.updateElement('cacheSize', `${Math.round((STATE.systemData.cache_size || 0) / 1024 / 1024)} MB`);
        this.updateElement('networkTraffic', `${(sys.network_current || 0).toFixed(1)} MB/s`);

        // Update performance bars
        this.updateProgressBar('cpuBar', sys.cpu_current);
        this.updateElement('cpuText', `${Math.round(sys.cpu_current)}% • ${sys.cpu_count || 8} cores active`);
        
        this.updateProgressBar('memoryBar', sys.memory_current);
        const memoryTotal = UI.formatBytes(sys.memory_total || 0);
        const memoryUsed = UI.formatBytes((sys.memory_current / 100) * (sys.memory_total || 0));
        this.updateElement('memoryText', `${Math.round(sys.memory_current)}% • ${memoryUsed} used of ${memoryTotal}`);
        
        const diskUsage = sys.disk_current || 0;
        this.updateProgressBar('diskBar', diskUsage);
        const diskTotal = UI.formatBytes(sys.disk_total || 0);
        const diskFree = UI.formatBytes(sys.disk_free || 0);
        this.updateElement('diskText', `${Math.round(diskUsage)}% • ${diskFree} free of ${diskTotal}`);

        // Update system status
        this.determineSystemStatus(sys, totalCameras);
        
        // Load alerts
        this.loadAlerts();
    },

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element && element.textContent !== String(value)) {
            element.textContent = value;
        }
    },

    updateProgressBar(id, percentage) {
        const element = document.getElementById(id);
        if (element) {
            const newWidth = `${Math.min(100, Math.max(0, percentage))}%`;
            if (element.style.width !== newWidth) {
                element.style.width = newWidth;
            }
        }
    },

    determineSystemStatus(sys, totalCameras) {
        const cpuHigh = sys.cpu_current > 80;
        const memoryHigh = sys.memory_current > 85;
        const camerasLow = sys.active_cameras < (totalCameras * 0.7);
        
        if (cpuHigh || memoryHigh || camerasLow) {
            if (sys.active_cameras < (totalCameras * 0.4) || sys.cpu_current > 95 || sys.memory_current > 95) {
                UI.updateSystemStatus('offline');
            } else {
                UI.updateSystemStatus('warning');
            }
        } else {
            UI.updateSystemStatus('online');
        }
    },

    async loadAlerts() {
        const alertData = await API.getSystemAlerts();
        if (alertData) {
            this.updateElement('systemAlerts', alertData.total_alerts || 0);
            this.updateElement('criticalAlerts', alertData.critical_alerts || 0);
        }
        
        const recordingSize = Object.keys(STATE.systemData.recordings || {}).length * 0.5;
        this.updateElement('recordingSize', `${recordingSize.toFixed(1)} GB`);
    },

    updateCharts() {
        if (!STATE.systemData.system || !STATE.charts.cpu) return;

        const now = new Date().toLocaleTimeString();
        const sys = STATE.systemData.system;

        // Update performance history
        STATE.performanceHistory.timestamps.push(now);
        STATE.performanceHistory.cpu.push(sys.cpu_current);
        STATE.performanceHistory.memory.push(sys.memory_current);
        STATE.performanceHistory.network.push(sys.network_current || 0);

        // Keep only last 20 data points
        if (STATE.performanceHistory.timestamps.length > 20) {
            STATE.performanceHistory.timestamps.shift();
            STATE.performanceHistory.cpu.shift();
            STATE.performanceHistory.memory.shift();
            STATE.performanceHistory.network.shift();
        }

        // Update charts
        this.updateChart(STATE.charts.cpu, STATE.performanceHistory.timestamps, STATE.performanceHistory.cpu);
        this.updateChart(STATE.charts.memory, STATE.performanceHistory.timestamps, STATE.performanceHistory.memory);
        this.updateChart(STATE.charts.network, STATE.performanceHistory.timestamps, STATE.performanceHistory.network);

        // Update camera status chart
        if (STATE.charts.camera) {
            const totalCameras = STATE.cameras.length || CONFIG.TOTAL_CAMERAS;
            const online = sys.active_cameras;
            const offline = totalCameras - online;
            const unstable = Math.floor(offline * 0.1);
            const actualOffline = offline - unstable;
            
            STATE.charts.camera.data.datasets[0].data = [online, actualOffline, unstable];
            STATE.charts.camera.update('none');
        }
    },

    updateChart(chart, labels, data) {
        if (!chart || !chart.data) return;
        
        // Only update if data has changed
        const currentData = chart.data.datasets[0].data;
        const hasChanged = data.length !== currentData.length || 
                          data.some((val, idx) => val !== currentData[idx]);
        
        if (hasChanged) {
            chart.data.labels = [...labels];
            chart.data.datasets[0].data = [...data];
            chart.update('none');
        }
    }
};
