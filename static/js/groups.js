// Camera Groups Module

const Groups = {
    groups: {
        'All Cameras': { cameras: [], color: '#00ff88' },
        'USA': { cameras: [], color: '#00d4ff' },
        'Europe': { cameras: [], color: '#ffa500' },
        'Asia': { cameras: [], color: '#ff4757' },
        'Company A': { cameras: [], color: '#FFB300' },
        'Private': { cameras: [], color: '#800080' }
    },

    initialize() {
        this.categorizeCamera();
        this.createGroupsUI();
    },

    categorizeCamera() {
        if (!STATE.cameras) return;

        // Reset groups
        Object.keys(this.groups).forEach(key => {
            this.groups[key].cameras = [];
        });

        STATE.cameras.forEach((camera, index) => {
            // Add to All Cameras
            this.groups['All Cameras'].cameras.push(index);

            // Categorize by location
            const name = camera.name.toLowerCase();
            if (name.includes('usa')) {
                this.groups['USA'].cameras.push(index);
            } else if (name.includes('europe') || name.includes('netherlands') || 
                       name.includes('turkey') || name.includes('russia') || 
                       name.includes('germany') || name.includes('italy') || 
                       name.includes('france')) {
                this.groups['Europe'].cameras.push(index);
            } else if (name.includes('china') || name.includes('japan') || 
                       name.includes('korea') || name.includes('taiwan')) {
                this.groups['Asia'].cameras.push(index);
            }

            // Categorize by company
            if (camera.company === 'Company A') {
                this.groups['Company A'].cameras.push(index);
            }

            // Categorize by NSFW
            if (camera.nsfw) {
                this.groups['Private'].cameras.push(index);
            }
        });
    },

    createGroupsUI() {
        const camerasTab = document.getElementById('cameras');
        if (!camerasTab) return;

        const searchContainer = camerasTab.querySelector('.search-container');
        if (!searchContainer) return;

        // Create groups container
        const groupsContainer = document.createElement('div');
        groupsContainer.className = 'groups-container';
        groupsContainer.style.cssText = `
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        `;

        // Create group buttons
        Object.entries(this.groups).forEach(([name, data]) => {
            if (data.cameras.length === 0 && name !== 'All Cameras') return;

            const button = document.createElement('button');
            button.className = 'btn btn-secondary group-btn';
            button.style.cssText = `
                border-left: 4px solid ${data.color};
                transition: all 0.3s ease;
            `;
            button.innerHTML = `
                <i class="fas fa-folder"></i>
                ${name}
                <span style="background: ${data.color}; color: #000; padding: 0.2rem 0.5rem; border-radius: 12px; margin-left: 0.5rem; font-size: 0.8rem; font-weight: bold;">
                    ${data.cameras.length}
                </span>
            `;
            button.onclick = () => this.showGroup(name);
            groupsContainer.appendChild(button);
        });

        searchContainer.after(groupsContainer);
    },

    showGroup(groupName) {
        const group = this.groups[groupName];
        if (!group) return;

        const grid = document.getElementById('cameraGrid');
        if (!grid) return;

        const cards = grid.querySelectorAll('.camera-card');
        
        cards.forEach((card, index) => {
            card.style.display = group.cameras.includes(index) ? 'block' : 'none';
        });

        // Update result count
        const countElement = document.getElementById('searchResultCount');
        if (countElement) {
            if (groupName === 'All Cameras') {
                countElement.textContent = '';
            } else {
                countElement.textContent = `(${group.cameras.length} cameras in ${groupName})`;
            }
        }

        // Highlight active group button
        document.querySelectorAll('.group-btn').forEach(btn => {
            btn.style.opacity = btn.textContent.includes(groupName) ? '1' : '0.6';
        });

        UI.showNotification(`Showing ${groupName}`, 'info');
    }
};
