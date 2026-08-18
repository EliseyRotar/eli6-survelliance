// Performance Optimization Module

const Performance = {
    // Debounce function to prevent excessive calls
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle function for scroll/resize events
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Lazy load images
    lazyLoadImages() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    },

    // Optimize DOM updates
    batchDOMUpdates(updates) {
        requestAnimationFrame(() => {
            updates.forEach(update => update());
        });
    },

    // Monitor performance
    monitor() {
        if (window.performance && window.performance.memory) {
            const memory = window.performance.memory;
            console.log('Memory Usage:', {
                used: (memory.usedJSHeapSize / 1048576).toFixed(2) + ' MB',
                total: (memory.totalJSHeapSize / 1048576).toFixed(2) + ' MB',
                limit: (memory.jsHeapSizeLimit / 1048576).toFixed(2) + ' MB'
            });
        }
    },

    // Clear unused data
    cleanup() {
        // Clear old performance history
        if (STATE.performanceHistory.timestamps.length > 100) {
            STATE.performanceHistory.timestamps = STATE.performanceHistory.timestamps.slice(-50);
            STATE.performanceHistory.cpu = STATE.performanceHistory.cpu.slice(-50);
            STATE.performanceHistory.memory = STATE.performanceHistory.memory.slice(-50);
            STATE.performanceHistory.network = STATE.performanceHistory.network.slice(-50);
        }
    }
};
