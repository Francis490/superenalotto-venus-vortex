const CACHE = "titan-cache-v1";
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./venus_database.json",
  "./vortex_chart.png",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Network-first per JSON e PNG (dati sempre freschi)
  if (url.pathname.endsWith(".json") || url.pathname.endsWith(".png")) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(request, clone));
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first per il resto
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
