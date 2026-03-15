const CACHE = "jrvs-v2";
const STATIC = ["/","/static/manifest.json"];

self.addEventListener("install",e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener("activate",e=>{
  e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch",e=>{
  const url=new URL(e.request.url);
  if(["/chat","/upload","/memory","/notes","/tasks","/tools","/sessions"].some(p=>url.pathname.startsWith(p))){
    e.respondWith(fetch(e.request).catch(()=>new Response(JSON.stringify({error:"Offline"}),{headers:{"Content-Type":"application/json"}})));
    return;
  }
  e.respondWith(caches.match(e.request).then(cached=>cached||fetch(e.request)));
});
