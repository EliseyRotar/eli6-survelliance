// Global Error Handler Module

const ErrorHandler = {
    // Initialize error handling
    initialize() {
        // Global error handler
        window.addEventListener('error', (event) => {
            this.logError('JavaScript Error', event.error);
            event.preventDefault();
        });

        // Unhandled promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            this.logError('Unhandled Promise Rejection', event.reason);
            event.preventDefault();
        });

        // Network error handler
        window.addEventListener('offline', () => {
            UI.showNotification('Network connection lost', 'error');
            UI.updateSystemStatus('offline');
        });

        window.addEventListener('online', () => {
            UI.showNotification('Network connection restored', 'success');
            Dashboard.update();
        });
    },

    // Log errors
    logError(type, error) {
        console.error(`[${type}]`, error);
        
        // Show user-friendly message
        const message = this.getUserFriendlyMessage(error);
        UI.showNotification(message, 'error');
        
        // Could send to logging service here
        this.sendToLoggingService(type, error);
    },

    // Get user-friendly error message
    getUserFriendlyMessage(error) {
        if (!error) return 'An unknown error occurred';
        
        const errorString = error.toString().toLowerCase();
        
        if (errorString.includes('network') || errorString.includes('fetch')) {
            return 'Network error - please check your connection';
        }
        if (errorString.includes('timeout')) {
            return 'Request timed out - please try again';
        }
        if (errorString.includes('permission')) {
            return 'Permission denied';
        }
        
        return 'An error occurred - please refresh the page';
    },

    // Send to logging service (placeholder)
    sendToLoggingService(type, error) {
        // In production, send to logging service
        // For now, just log to console
        if (window.location.hostname !== 'localhost') {
            // Would send to remote logging service
        }
    },

    // Retry failed requests
    async retryRequest(requestFunc, maxRetries = 3, delay = 1000) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await requestFunc();
            } catch (error) {
                if (i === maxRetries - 1) throw error;
                await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
            }
        }
    }
};
