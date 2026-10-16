// DIGI-FEED v16 (expanded global feeds & multilingual sources)
const CACHE_NAME = 'digi-feed-v16';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './digimon_feeds.json',
  './data/dex.json',
  './data/digimon_all_index.json',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Network First, 같은 출처 파일만 캐시 (외부 API·이미지 응답은 캐시하지 않음)
// ?t=타임스탬프 같은 쿼리를 제거한 주소로 저장해 캐시가 무한히 늘어나지 않도록 함
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const cacheKey = url.origin + url.pathname;

  event.respondWith(
    fetch(req)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(cacheKey, responseClone));
        }
        return networkResponse;
      })
      .catch(() => caches.match(cacheKey).then((hit) => hit || caches.match(req)))
  );
});
