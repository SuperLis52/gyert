const CACHE_NAME = 'gyert-v2';
const STATIC_ASSETS = [
  '/static/js/app.js?v=4',
  '/static/css/main.css?v=4',
  '/static/logo-default.png',
  '/static/logo-dark.png',
  '/static/logo-light.png',
  '/static/favicon.png',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
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
  // Для HTML и API – всегда сеть
  if (event.request.mode === 'navigate' || event.request.url.includes('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }
  // Для статики – кэш, потом сеть
  event.respondWith(
    caches.match(event.request).then(cached => {
      return cached || fetch(event.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});