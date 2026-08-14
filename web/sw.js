// 駅さがし Service Worker: アプリシェル + データを先読みキャッシュ
const CACHE = 'eki-sagashi-vae3cb84';
const ASSETS = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './search.js',
  './index-worker.js',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './stations.json',
  './canon.json',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  e.respondWith(
    // ?v=ae3cb84 等クエリを無視してキャッシュ照合（バージョン違いによるinstall失敗を防ぐ）
    caches.match(e.request, { ignoreSearch: true }).then((hit) => {
      if (hit) return hit;
      return fetch(e.request).then((res) => {
        if (res.ok && (url.pathname.endsWith('.json') || url.pathname.endsWith('.js') ||
                       url.pathname.endsWith('.css') || url.pathname.endsWith('.png'))) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      });
    })
  );
});
