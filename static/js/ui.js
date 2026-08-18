// UI Management Module

const UI = {
    showTab(tabName) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
            content.style.display = 'none';
        });
        
        const activeTab = document.getElementById(tabName);
        if (activeTab) {
            activeTab.classList.add('active');
            activeTab.style.display = 'block';
        }

        STATE.currentTab = tabName;

        // Load tab-specific data
        switch(tabName) {
            case 'cameras':
                Cameras.load();
                break;
            case 'recordings':
                Recordings.load();
                break;
            case 'analytics':
                Analytics.load();
                break;
        }
    },

    updateSystemStatus(status) {
        const statusDot = document.getElementById('systemStatus');
        const statusText = document.getElementById('systemStatusText');
        
        if (statusDot && statusText) {
            statusDot.className = `status-dot status-${status}`;
            
            switch(status) {
                case 'online':
                    statusText.textContent = 'System Online';
                    break;
                case 'warning':
                    statusText.textContent = 'System Warning';
                    break;
                case 'offline':
                    statusText.textContent = 'System Offline';
                    break;
            }
        }
    },

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    },

    formatUptime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    },

    formatBytes(bytes) {
        if (bytes === 0) return '0 GB';
        const gb = bytes / (1024 ** 3);
        return `${gb.toFixed(1)} GB`;
    }
};
