const CACHE_VERSION = "v1";
const CACHE = `venus-vortex-cache-${CACHE_VERSION}`;

const ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
  "./favicon.ico"
];

// Install: pre-cache degli asset principali
self.addEventListener("install", (event) => {
  console.log(`[SW] Installing ${CACHE}`);
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate: pulizia cache vecchie
self.addEventListener("activate", (event) => {
  console.log(`[SW] Activating ${CACHE}`);
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Fetch
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Network-first per JSON e PNG (dati sempre freschi)
  if (url.pathname.endsWith(".json") || url.pathname.endsWith(".png")) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const clone = res.clone();
          event.waitUntil(
            caches.open(CACHE).then((c) => c.put(request, clone))
          );
          return res;
        })
        .catch(() =>
          caches.match(request).then((cached) =>
            cached || new Response("", { status: 503, statusText: "Offline" })
          )
        )
    );
    return;
  }

  // Cache-first per il resto
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
