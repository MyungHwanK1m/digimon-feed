// DIGI-FEED v20 (network-first with timeout, no unused precache, ETag revalidation instead of ?t= cache-busting)
const CACHE_NAME = 'digi-feed-v20';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './digimon_feeds.json',
  './data/dex.json',
  './icon-192.png',
  './icon-512.png'
];
// 네트워크가 이 시간 안에 응답하지 않으면(약한 신호 등) 캐시된 사본으로 먼저 응답
const NETWORK_TIMEOUT_MS = 4500;

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
// 쿼리(?v= 등)를 제거한 주소로 저장해 캐시가 무한히 늘어나지 않도록 함
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const cacheKey = url.origin + url.pathname;
  const networkPromise = fetch(req);

  // 캐시 저장은 waitUntil 안에서 끝까지 수행 (응답을 먼저 돌려줘도 SW가 중간에 종료되지 않도록)
  event.waitUntil(
    networkPromise
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseClone = networkResponse.clone();
          return caches.open(CACHE_NAME).then((cache) => cache.put(cacheKey, responseClone));
        }
      })
      .catch(() => {})
  );

  event.respondWith((async () => {
    const cached = (await caches.match(cacheKey)) || (await caches.match(req));
    if (!cached) return networkPromise; // 캐시가 없으면 네트워크 결과(또는 오류)를 그대로
    let timer;
    const timeout = new Promise((resolve) => {
      timer = setTimeout(() => resolve(cached), NETWORK_TIMEOUT_MS);
    });
    try {
      return await Promise.race([networkPromise.catch(() => cached), timeout]);
    } finally {
      clearTimeout(timer);
    }
  })());
});
