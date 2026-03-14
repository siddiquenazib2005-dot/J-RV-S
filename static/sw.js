// J-RV-S Service Worker — PWA Support
// By Nazib Siddique

const CACHE_NAME = "jrvs-v1";
const STATIC_ASSETS = [
  "/",
  "/static/manifest.json",
  "/ping"
];

// Install — cache static assets
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch — network first, cache fallback
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  // Always network for API calls
  if (url.pathname.startsWith("/chat") ||
      url.pathname.startsWith("/upload") ||
      url.pathname.startsWith("/memory") ||
      url.pathname.startsWith("/notes") ||
      url.pathname.startsWith("/tasks") ||
      url.pathname.startsWith("/tools")) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: "Offline — No internet connection" }), {
          headers: { "Content-Type": "application/json" }
        })
      )
    );
    return;
  }

  // Cache first for static, fallback to network
  event.respondWith(
    caches.match(event.request).then(cached => {
      return cached || fetch(event.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    }).catch(() => caches.match("/"))
  );
});

// Push notifications (future use)
self.addEventListener("push", event => {
  const data = event.data ? event.data.json() : { title: "J-RV-S", body: "New message" };
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/static/icon-192.png",
      badge: "/static/icon-192.png",
      vibrate: [100, 50, 100]
    })
  );
});
