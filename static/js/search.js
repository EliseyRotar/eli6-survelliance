// Camera Search and Filter Module

const Search = {
    currentFilter: {
        text: '',
        status: 'all',
        type: 'all',
        company: 'all'
    },

    initialize() {
        this.createSearchUI();
        this.setupEventListeners();
    },

    createSearchUI() {
        const camerasTab = document.getElementById('cameras');
        if (!camerasTab) return;

        const header = camerasTab.querySelector('div');
        if (!header) return;

        // Create search container
        const searchContainer = document.createElement('div');
        searchContainer.className = 'search-container';
        searchContainer.style.cssText = `
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 1rem;
            margin-bottom: 2rem;
            padding: 1.5rem;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            backdrop-filter: blur(20px);
        `;

        searchContainer.innerHTML = `
            <div>
                <input type="text" 
                       id="cameraSearch" 
                       placeholder="🔍 Search cameras by name, location, or URL..."
                       style="width: 100%; padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border); background: var(--accent-color); color: var(--text-primary); font-size: 0.9rem;">
            </div>
            <div>
                <select id="statusFilter" style="width: 100%; padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border); background: var(--accent-color); color: var(--text-primary); font-size: 0.9rem;">
                    <option value="all">All Status</option>
                    <option value="online">Online</option>
                    <option value="offline">Offline</option>
                    <option value="unstable">Unstable</option>
                </select>
            </div>
            <div>
                <select id="typeFilter" style="width: 100%; padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border); background: var(--accent-color); color: var(--text-primary); font-size: 0.9rem;">
                    <option value="all">All Types</option>
                    <option value="video">Video</option>
                    <option value="image">Image</option>
                </select>
            </div>
            <div>
                <select id="companyFilter" style="width: 100%; padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border); background: var(--accent-color); color: var(--text-primary); font-size: 0.9rem;">
                    <option value="all">All Companies</option>
                </select>
            </div>
        `;

        // Insert after header
        header.after(searchContainer);

        // Populate company filter
        this.populateCompanyFilter();
    },

    setupEventListeners() {
        const searchInput = document.getElementById('cameraSearch');
        const statusFilter = document.getElementById('statusFilter');
        const typeFilter = document.getElementById('typeFilter');
        const companyFilter = document.getElementById('companyFilter');

        if (searchInput) {
            searchInput.addEventListener('input', Performance.debounce(() => {
                this.currentFilter.text = searchInput.value.toLowerCase();
                this.applyFilters();
            }, 300));
        }

        if (statusFilter) {
            statusFilter.addEventListener('change', () => {
                this.currentFilter.status = statusFilter.value;
                this.applyFilters();
            });
        }

        if (typeFilter) {
            typeFilter.addEventListener('change', () => {
                this.currentFilter.type = typeFilter.value;
                this.applyFilters();
            });
        }

        if (companyFilter) {
            companyFilter.addEventListener('change', () => {
                this.currentFilter.company = companyFilter.value;
                this.applyFilters();
            });
        }
    },

    populateCompanyFilter() {
        const companyFilter = document.getElementById('companyFilter');
        if (!companyFilter || !STATE.cameras) return;

        const companies = new Set();
        STATE.cameras.forEach(camera => {
            if (camera.company) {
                companies.add(camera.company);
            }
        });

        // Add companies to filter
        Array.from(companies).sort().forEach(company => {
            const option = document.createElement('option');
            option.value = company;
            option.textContent = company;
            companyFilter.appendChild(option);
        });
    },

    applyFilters() {
        const grid = document.getElementById('cameraGrid');
        if (!grid) return;

        const cards = grid.querySelectorAll('.camera-card');
        let visibleCount = 0;

        cards.forEach((card, index) => {
            const camera = STATE.cameras[index];
            if (!camera) return;

            let visible = true;

            // Text search
            if (this.currentFilter.text) {
                const searchText = this.currentFilter.text;
                const matchName = camera.name.toLowerCase().includes(searchText);
                const matchUrl = camera.url.toLowerCase().includes(searchText);
                const matchCompany = (camera.company || '').toLowerCase().includes(searchText);
                
                visible = visible && (matchName || matchUrl || matchCompany);
            }

            // Status filter
            if (this.currentFilter.status !== 'all') {
                const statusDot = card.querySelector('.status-dot');
                if (statusDot) {
                    const hasStatus = statusDot.classList.contains(`status-${this.currentFilter.status}`);
                    visible = visible && hasStatus;
                }
            }

            // Type filter
            if (this.currentFilter.type !== 'all') {
                visible = visible && (camera.type === this.currentFilter.type);
            }

            // Company filter
            if (this.currentFilter.company !== 'all') {
                visible = visible && (camera.company === this.currentFilter.company);
            }

            // Show/hide card
            card.style.display = visible ? 'block' : 'none';
            if (visible) visibleCount++;
        });

        // Show result count
        this.updateResultCount(visibleCount, STATE.cameras.length);
    },

    updateResultCount(visible, total) {
        let countElement = document.getElementById('searchResultCount');
        
        if (!countElement) {
            const camerasTab = document.getElementById('cameras');
            const header = camerasTab.querySelector('h2');
            if (header) {
                countElement = document.createElement('span');
                countElement.id = 'searchResultCount';
                countElement.style.cssText = 'margin-left: 1rem; font-size: 0.9rem; color: var(--text-secondary);';
                header.appendChild(countElement);
            }
        }

        if (countElement) {
            if (visible === total) {
                countElement.textContent = '';
            } else {
                countElement.textContent = `(${visible} of ${total} cameras)`;
            }
        }
    },

    reset() {
        this.currentFilter = {
            text: '',
            status: 'all',
            type: 'all',
            company: 'all'
        };

        const searchInput = document.getElementById('cameraSearch');
        const statusFilter = document.getElementById('statusFilter');
        const typeFilter = document.getElementById('typeFilter');
        const companyFilter = document.getElementById('companyFilter');

        if (searchInput) searchInput.value = '';
        if (statusFilter) statusFilter.value = 'all';
        if (typeFilter) typeFilter.value = 'all';
        if (companyFilter) companyFilter.value = 'all';

        this.applyFilters();
    }
};
