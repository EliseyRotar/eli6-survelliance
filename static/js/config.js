// Configuration and Global Variables
const CONFIG = {
    API_BASE: '',
    REFRESH_INTERVAL: 2000,
    CHART_UPDATE_INTERVAL: 10000,
    TOTAL_CAMERAS: 88
};

// Global State
const STATE = {
    currentTab: 'dashboard',
    systemData: {},
    cameras: [],
    recordings: {},
    selectedCamera: null,
    charts: {},
    performanceHistory: {
        timestamps: [],
        cpu: [],
        memory: [],
        network: []
    }
};

// Company Colors for Camera Identification
const COMPANY_COLORS = {
    'Company A': '#FFB300',
    'Axis Communications': '#FF69B4',
    'Private House': '#800080',
    'Korea Cams': '#32CD32',
    'Korea Multi-Cam': '#FFD700',
    'Netherlands Cams': '#FF4500',
    'Turkey Multi-Cam': '#DC143C'
};
