// Main Application Module

const App = {
    async initialize() {
        console.log('🚀 Initializing ELI6 Surveillance System...');
        
        // Initialize error handling first
        ErrorHandler.initialize();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize charts
        Charts.initialize();
        
        // Load initial data
        await this.loadInitialData();
        
        // Show dashboard
        UI.showTab('dashboard');
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Start performance monitoring
        this.startPerformanceMonitoring();
        
        console.log('✅ System initialized successfully');
    },

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = link.dataset.tab;
                UI.showTab(tab);
            });
        });

        // Modal close on outside click
        const modal = document.getElementById('cameraModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    Cameras.closeModal();
                }
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && STATE.selectedCamera !== null) {
                Cameras.closeModal();
            }
        });
    },

    async loadInitialData() {
        STATE.cameras = await API.getCameras();
        await Dashboard.update();
    },

    startAutoRefresh() {
        // Refresh system status every 2 seconds
        setInterval(async () => {
            try {
                await Dashboard.update();
            } catch (error) {
                console.error('Dashboard update error:', error);
            }
        }, CONFIG.REFRESH_INTERVAL);
        
        // Refresh current tab data every 10 seconds
        setInterval(() => {
            try {
                switch(STATE.currentTab) {
                    case 'recordings':
                        Recordings.load();
                        break;
                    case 'analytics':
                        Analytics.load();
                        break;
                }
            } catch (error) {
                console.error('Tab refresh error:', error);
            }
        }, CONFIG.CHART_UPDATE_INTERVAL);
    },

    startPerformanceMonitoring() {
        // Clean up old data every minute
        setInterval(() => {
            Performance.cleanup();
        }, 60000);
        
        // Monitor performance every 5 minutes (development only)
        if (window.location.hostname === 'localhost') {
            setInterval(() => {
                Performance.monitor();
            }, 300000);
        }
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.initialize();
});
