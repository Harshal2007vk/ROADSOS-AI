const CACHE_NAME = 'roadsos-v2';
const STATIC_ASSETS = [
    '/',
    '/dashboard',
    '/map',
    '/profile',
    '/disaster',
    '/sos',
    '/static/js/app.js',
    '/static/js/service-worker.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdn.tailwindcss.com'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    // Network first, falling back to cache
    event.respondWith(
        fetch(event.request)
            .catch(() => caches.match(event.request))
    );
});

self.addEventListener('sync', event => {
    if (event.tag === 'sync-sos') {
        event.waitUntil(syncOfflineSOS());
    }
});

async function syncOfflineSOS() {
    // Logic to sync offline requests from IndexedDB
    console.log("Background sync triggered for offline SOS.");
}
