// PWA Service Worker Registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/service-worker.js')
            .then(reg => console.log('ServiceWorker registered:', reg))
            .catch(err => console.log('ServiceWorker registration failed:', err));
    });
}

// Network Status Handling
const updateOnlineStatus = () => {
    const indicator = document.getElementById('offline-indicator');
    if (indicator) {
        if (!navigator.onLine) {
            indicator.classList.remove('hidden');
            indicator.classList.add('flex');
        } else {
            indicator.classList.add('hidden');
            indicator.classList.remove('flex');
            // Try to sync offline data when back online
            syncOfflineData();
        }
    }
};

window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);
document.addEventListener('DOMContentLoaded', updateOnlineStatus);

// IndexedDB Setup for Offline Storage
const dbName = 'roadsos-db';
const request = indexedDB.open(dbName, 1);

request.onupgradeneeded = (event) => {
    const db = event.target.result;
    if (!db.objectStoreNames.contains('sos-queue')) {
        db.createObjectStore('sos-queue', { keyPath: 'id', autoIncrement: true });
    }
};

request.onerror = (event) => {
    console.error('IndexedDB error:', event.target.errorCode);
};

// Mock sync offline data function
function syncOfflineData() {
    console.log("Checking for offline data to sync...");
    // Ideally query IndexedDB for 'sos-queue' and POST to backend
}
