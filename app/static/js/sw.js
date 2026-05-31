// ROADSoS AI Service Worker v1.0
const CACHE_NAME = 'roadsos-v1';
const STATIC_CACHE = 'roadsos-static-v1';

const STATIC_ASSETS = [
    '/',
    '/sos',
    '/map',
    '/dashboard',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => console.warn('Cache partial fail:', err));
        }).then(() => self.skipWaiting())
    );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter(k => k !== CACHE_NAME && k !== STATIC_CACHE).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

// Fetch strategy: Network first, cache fallback
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET and API calls (except for offline queuing)
    if (request.method !== 'GET') return;

    // API routes: network only (with offline fallback response)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request).catch(() =>
                new Response(JSON.stringify({ error: 'offline', message: 'You are offline. Please reconnect.' }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                })
            )
        );
        return;
    }

    // HTML pages: Network first, stale-while-revalidate
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request)
                .then(res => {
                    const clone = res.clone();
                    caches.open(CACHE_NAME).then(c => c.put(request, clone));
                    return res;
                })
                .catch(() =>
                    caches.match(request).then(cached => cached || caches.match('/'))
                )
        );
        return;
    }

    // Static assets: Cache first
    event.respondWith(
        caches.match(request).then(cached => {
            if (cached) return cached;
            return fetch(request).then(res => {
                const clone = res.clone();
                caches.open(STATIC_CACHE).then(c => c.put(request, clone));
                return res;
            });
        })
    );
});

// Background sync for offline SOS
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-sos') {
        event.waitUntil(syncOfflineSOS());
    }
});

async function syncOfflineSOS() {
    const db = await openOfflineDB();
    const pending = await db.getAll('pending_sos');
    for (const item of pending) {
        try {
            const res = await fetch('/api/sos/trigger', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item.data)
            });
            if (res.ok) await db.delete('pending_sos', item.id);
        } catch (e) {
            console.warn('Sync failed for:', item.id);
        }
    }
}

// Push notifications
self.addEventListener('push', (event) => {
    const data = event.data?.json() || { title: 'ROADSoS AI', body: 'Emergency alert' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icons/icon-192.png',
            badge: '/static/icons/icon-192.png',
            vibrate: [300, 100, 400],
            tag: 'roadsos-alert',
            requireInteraction: true,
            actions: [
                { action: 'open', title: 'Open App' },
                { action: 'call', title: 'Call 112' }
            ]
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.action === 'call') {
        clients.openWindow('tel:112');
    } else {
        clients.openWindow('/dashboard');
    }
});
