// Camera Management Module - OPTIMIZED for performance

const Cameras = {
    visibleCameras: new Set(),
    loadedCameras: new Set(),
    intersectionObserver: null,
    
    async load() {
        STATE.cameras = await API.getCameras();
        this.setupLazyLoading();
        this.display();
        
        // Initialize search and groups after cameras are loaded
        if (typeof Search !== 'undefined') {
            Search.initialize();
        }
        if (typeof Groups !== 'undefined') {
            Groups.initialize();
        }
    },

    setupLazyLoading() {
        // Create intersection observer for lazy loading
        this.intersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const cameraIndex = parseInt(entry.target.dataset.cameraIndex);
                if (entry.isIntersecting) {
                    this.visibleCameras.add(cameraIndex);
                    this.loadCameraFeed(cameraIndex);
                } else {
                    this.visibleCameras.delete(cameraIndex);
                    this.unloadCameraFeed(cameraIndex);
                }
            });
        }, {
            rootMargin: '100px', // Start loading 100px before entering viewport
            threshold: 0.1
        });
    },

    display() {
        const grid = document.getElementById('cameraGrid');
        if (!grid) return;

        grid.innerHTML = '';

        // Create camera cards with lazy loading
        STATE.cameras.forEach((camera, index) => {
            const card = document.createElement('div');
            card.className = 'camera-card';
            card.dataset.cameraIndex = index;
            
            const statusClass = STATE.systemData.cameras && STATE.systemData.cameras[index] 
                ? STATE.systemData.cameras[index].status 
                : 'unknown';
            
            const isRecording = STATE.systemData.recordings && STATE.systemData.recordings[index];
            const company = camera.company || 'Unknown';
            const companyColor = COMPANY_COLORS[company];
            const isNSFW = camera.nsfw || false;
            
            if (companyColor) {
                card.style.borderLeft = `5px solid ${companyColor}`;
            }
            
            card.innerHTML = `
                <div class="camera-header">
                    <div class="camera-name">
                        <i class="fas fa-${camera.type === 'video' ? 'video' : 'camera'}"></i>
                        ${camera.name}
                        ${isNSFW ? '<i class="fas fa-eye-slash" style="color: #ff0000; margin-left: 5px;" title="Private Content"></i>' : ''}
                        ${companyColor ? `<div style="font-size: 0.7rem; color: ${companyColor}; margin-top: 2px;">
                            <i class="fas fa-building"></i> ${company}
                        </div>` : ''}
                    </div>
                    <div class="camera-status">
                        ${isRecording ? '<i class="fas fa-record-vinyl" style="color: var(--danger-color);"></i>' : ''}
                        <div class="status-dot status-${statusClass === 'online' ? 'online' : statusClass === 'unstable' ? 'warning' : 'offline'}"></div>
                    </div>
                </div>
                <div class="camera-feed-container">
                    <div class="camera-placeholder" id="placeholder-${index}">
                        <div class="loading-spinner">
                            <i class="fas fa-spinner fa-spin"></i>
                            <div>Loading Camera ${index + 1}...</div>
                        </div>
                    </div>
                    <img class="camera-feed ${isNSFW ? 'nsfw-blurred' : ''}" 
                         id="camera-${index}"
                         style="display: none;"
                         alt="${camera.name}"
                         onclick="Cameras.openModal(${index})"
                         onerror="this.style.display='none'; document.getElementById('placeholder-${index}').innerHTML='<div class=\\"camera-error\\"><i class=\\"fas fa-exclamation-triangle\\"></i><div>Camera Offline</div></div>'">
                    ${isNSFW ? `
                        <div class="nsfw-overlay" onclick="Cameras.openModal(${index})">
                            <div class="nsfw-warning">
                                <i class="fas fa-eye-slash fa-2x"></i>
                                <div>PRIVATE CONTENT</div>
                                <div style="font-size: 0.8rem;">Click to view</div>
                            </div>
                        </div>
                    ` : ''}
                </div>
                <div class="camera-controls">
                    <div class="camera-info">
                        ${camera.type === 'video' ? 'Live Stream' : 'Static Image'} • 
                        ${statusClass.charAt(0).toUpperCase() + statusClass.slice(1)}
                        ${isNSFW ? ' • Private' : ''}
                    </div>
                    <div class="camera-actions">
                        <button class="btn btn-secondary" onclick="Cameras.refresh(${index})" aria-label="Refresh camera ${index + 1}">
                            <i class="fas fa-sync-alt"></i>
                        </button>
                        <button class="btn ${isRecording ? 'btn-danger' : 'btn-primary'}" 
                                onclick="Cameras.toggleRecording(${index})"
                                aria-label="${isRecording ? 'Stop' : 'Start'} recording camera ${index + 1}">
                            <i class="fas fa-${isRecording ? 'stop' : 'record-vinyl'}"></i>
                        </button>
                    </div>
                </div>
            `;
            
            grid.appendChild(card);
            
            // Observe this camera card for lazy loading
            this.intersectionObserver.observe(card);
        });
    },

    loadCameraFeed(cameraIndex) {
        if (this.loadedCameras.has(cameraIndex)) return;
        
        const img = document.getElementById(`camera-${cameraIndex}`);
        const placeholder = document.getElementById(`placeholder-${cameraIndex}`);
        
        if (img && placeholder) {
            // Use thumbnail for grid view to reduce load
            img.src = `/camera_thumbnail/${cameraIndex}?t=${Date.now()}`;
            
            let retryCount = 0;
            const maxRetries = 3;
            
            const tryLoad = () => {
                img.onload = () => {
                    img.style.display = 'block';
                    placeholder.style.display = 'none';
                    this.loadedCameras.add(cameraIndex);
                    
                    // Refresh thumbnail every 5 seconds for visible cameras
                    if (this.visibleCameras.has(cameraIndex)) {
                        setTimeout(() => {
                            if (this.visibleCameras.has(cameraIndex)) {
                                img.src = `/camera_thumbnail/${cameraIndex}?t=${Date.now()}`;
                            }
                        }, 5000);
                    }
                };
                
                img.onerror = () => {
                    retryCount++;
                    if (retryCount < maxRetries) {
                        // Retry after delay
                        setTimeout(() => {
                            console.log(`Retrying camera ${cameraIndex + 1} (attempt ${retryCount + 1})`);
                            img.src = `/camera_thumbnail/${cameraIndex}?t=${Date.now()}`;
                        }, 2000 * retryCount); // Increasing delay: 2s, 4s, 6s
                    } else {
                        // Show error after max retries
                        placeholder.innerHTML = `
                            <div class="camera-error">
                                <i class="fas fa-exclamation-triangle"></i>
                                <div>Camera ${cameraIndex + 1}</div>
                                <div style="font-size: 0.8rem;">Loading failed</div>
                            </div>
                        `;
                        console.warn(`Camera ${cameraIndex + 1} failed to load after ${maxRetries} attempts`);
                    }
                };
            };
            
            tryLoad();
        }
    },

    unloadCameraFeed(cameraIndex) {
        const img = document.getElementById(`camera-${cameraIndex}`);
        const placeholder = document.getElementById(`placeholder-${cameraIndex}`);
        
        if (img && placeholder) {
            img.style.display = 'none';
            img.src = '';
            placeholder.style.display = 'flex';
            placeholder.innerHTML = `
                <div class="loading-spinner">
                    <i class="fas fa-eye-slash"></i>
                    <div>Camera ${cameraIndex + 1}</div>
                </div>
            `;
            this.loadedCameras.delete(cameraIndex);
        }
    },

    openModal(cameraIndex) {
        STATE.selectedCamera = cameraIndex;
        const camera = STATE.cameras[cameraIndex];
        
        document.getElementById('modalCameraName').textContent = camera.name;
        // Use full video feed for modal (higher quality)
        document.getElementById('fullscreenCamera').src = `/camera_feed/${cameraIndex}?t=${Date.now()}`;
        document.getElementById('cameraDetails').textContent = 
            `${camera.type === 'video' ? 'Live Video Stream' : 'Static Image Camera'} • ${camera.url}`;
        
        const isRecording = STATE.systemData.recordings && STATE.systemData.recordings[cameraIndex];
        const recordBtn = document.getElementById('recordBtn');
        recordBtn.innerHTML = `<i class="fas fa-${isRecording ? 'stop' : 'record-vinyl'}"></i> ${isRecording ? 'Stop' : 'Record'}`;
        recordBtn.className = `btn ${isRecording ? 'btn-danger' : 'btn-primary'}`;
        
        document.getElementById('cameraModal').style.display = 'block';
    },

    closeModal() {
        document.getElementById('cameraModal').style.display = 'none';
        // Stop the video feed to save resources
        document.getElementById('fullscreenCamera').src = '';
        STATE.selectedCamera = null;
    },

    refresh(cameraIndex) {
        const img = document.getElementById(`camera-${cameraIndex}`);
        if (img && this.visibleCameras.has(cameraIndex)) {
            img.src = `/camera_thumbnail/${cameraIndex}?t=${Date.now()}`;
        }
    },

    refreshAll() {
        // Only refresh visible cameras to save resources
        this.visibleCameras.forEach(cameraIndex => {
            this.refresh(cameraIndex);
        });
        UI.showNotification(`Refreshed ${this.visibleCameras.size} visible cameras`, 'success');
    },

    async toggleRecording(cameraIndex) {
        const isRecording = STATE.systemData.recordings && STATE.systemData.recordings[cameraIndex];
        const endpoint = isRecording ? 'stop' : 'start';
        
        try {
            const response = await fetch(`/api/recording/${endpoint}/${cameraIndex}`);
            const result = await response.json();
            
            if (result.success) {
                await Dashboard.update();
                this.display();
                UI.showNotification(result.message, 'success');
            } else {
                UI.showNotification(result.message, 'error');
            }
        } catch (error) {
            UI.showNotification('Error toggling recording', 'error');
        }
    }
};
