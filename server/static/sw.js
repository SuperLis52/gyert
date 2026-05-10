const CV = 'gyert-v1';
const ASSETS = ['/','/feed','/static/css/main.css','/static/css/auth.css','/static/js/app.js'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CV).then(c => c.addAll(ASSETS).catch(()=>{})).then(()=>self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x=>x!==CV).map(x=>caches.delete(x)))).then(()=>clients.claim())); });
self.addEventListener('fetch', e => {
    if (e.request.url.includes('/api/')||e.request.url.includes('/socket.io/')) return;
    if (e.request.method!=='GET') return;
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(res => { if(res.ok){const cl=res.clone();caches.open(CV).then(c=>c.put(e.request,cl));} return res; }).catch(()=>caches.match('/feed'))));
});
self.addEventListener('push', e => {
    const d = e.data?e.data.json():{title:'Gyert',body:'Новое уведомление'};
    e.waitUntil(self.registration.showNotification(d.title,{body:d.body,icon:'/avatars/default.png',vibrate:[200,100,200]}));
});
self.addEventListener('notificationclick', e => { e.notification.close(); e.waitUntil(clients.openWindow('/feed')); });