// Recordings Management Module

const Recordings = {
    async load() {
        STATE.recordings = await API.getRecordingStatus();
        this.display();
    },

    display() {
        const list = document.getElementById('recordingsList');
        if (!list) return;
        
        if (Object.keys(STATE.recordings).length === 0) {
            list.innerHTML = `
                <div class="dashboard-card">
                    <div style="text-align: center; padding: 2rem;">
                        <i class="fas fa-record-vinyl fa-3x" style="color: var(--text-secondary); margin-bottom: 1rem;"></i>
                        <h3>No Active Recordings</h3>
                        <p style="color: var(--text-secondary);">Start recording from the camera view</p>
                    </div>
                </div>
            `;
            return;
        }

        list.innerHTML = '';
        Object.entries(STATE.recordings).forEach(([cameraId, recording]) => {
            const camera = STATE.cameras[parseInt(cameraId)];
            const duration = Math.floor(recording.duration);
            const hours = Math.floor(duration / 3600);
            const minutes = Math.floor((duration % 3600) / 60);
            const seconds = duration % 60;
            
            const card = document.createElement('div');
            card.className = 'dashboard-card';
            card.innerHTML = `
                <div class="card-header">
                    <div class="card-title">
                        <i class="fas fa-record-vinyl" style="color: var(--danger-color);"></i>
                        ${camera ? camera.name : `Camera ${cameraId}`}
                    </div>
                    <button class="btn btn-danger" onclick="Recordings.stop(${cameraId})">
                        <i class="fas fa-stop"></i> Stop
                    </button>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 1rem;">
                    <div>
                        <div class="card-subtitle">Duration</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">
                            ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}
                        </div>
                    </div>
                    <div>
                        <div class="card-subtitle">Frames</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">${recording.frame_count}</div>
                    </div>
                    <div>
                        <div class="card-subtitle">File</div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary);">${recording.filepath.split('/').pop()}</div>
                    </div>
                </div>
            `;
            list.appendChild(card);
        });
    },

    async stop(cameraId) {
        try {
            const response = await fetch(`/api/recording/stop/${cameraId}`);
            const result = await response.json();
            
            if (result.success) {
                await this.load();
                await Dashboard.update();
                UI.showNotification('Recording stopped successfully', 'success');
            } else {
                UI.showNotification(result.message, 'error');
            }
        } catch (error) {
            UI.showNotification('Error stopping recording', 'error');
        }
    }
};
