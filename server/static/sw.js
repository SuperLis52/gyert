const CACHE_NAME = 'gyert-v1';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
    );
    self.clients.claim();
});
self.addEventListener('fetch', e => {
    if (e.request.mode === 'navigate' || e.request.url.includes('/api/')) {
        e.respondWith(fetch(e.request));
        return;
    }
    e.respondWith(
        caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
            if (resp.ok) {
                const clone = resp.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
            }
            return resp;
        }))
    );
});
