// Authenticated WURFBILD: do not cache protected pages, scripts or user data.
// Offline editing will use a dedicated IndexedDB queue in a later phase.
self.addEventListener('install', event => { self.skipWaiting(); });
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  // Let the browser handle all requests online. No offline fallback for now.
});
