"use strict";
const STATE_CACHE = "gh-daily-state-v1";
const STATE_URL = "/__gh_daily_cache_state__";
const PREFIX = "gh-daily-content-";
const MAX_FILES = 2000;
const MAX_TOTAL = 64 * 1024 * 1024;
let pending = null;

function excluded(path) {
  return path.startsWith("/api/") || path === "/settings.html" || path === "/settings.js" || path === "/sw.js";
}
function safePath(path) {
  if (typeof path !== "string" || !path || path.length > 500 || /[\\%:#?]/.test(path) || path.startsWith("/")) return false;
  return path.split("/").every((part) => part && !part.startsWith("."));
}
async function announce(message) {
  const pages = await self.clients.matchAll({includeUncontrolled: true});
  pages.forEach((page) => page.postMessage(message));
}
async function currentState() {
  const state = await caches.open(STATE_CACHE);
  const response = await state.match(STATE_URL);
  return response ? response.json() : null;
}
async function cacheStatus() {
  const state = await currentState();
  if (state && await caches.has(state.cache)) await announce({type: "CACHE_READY", revision: state.revision});
}
async function performCache() {
  const manifestResponse = await fetch("/content-manifest.json", {cache: "no-store"});
  if (!manifestResponse.ok) throw new Error("清单未就绪");
  const manifest = await manifestResponse.json();
  if (!Array.isArray(manifest.files) || !manifest.files.length || manifest.files.length > MAX_FILES || !/^[a-zA-Z0-9_.-]{1,128}$/.test(manifest.revision)) throw new Error("清单不正确");
  const paths = new Set();
  let size = 0;
  manifest.files.forEach((entry) => {
    if (!safePath(entry.path) || paths.has(entry.path) || !/^[a-f0-9]{64}$/.test(entry.sha256) || !Number.isInteger(entry.size) || entry.size < 0 || entry.size > 16 * 1024 * 1024) throw new Error("文件不正确");
    paths.add(entry.path); size += entry.size;
  });
  if (size > MAX_TOTAL) throw new Error("清单过大");
  const entries = manifest.files.filter((entry) => !excluded("/" + entry.path));
  const name = PREFIX + manifest.revision;
  const previous = await currentState();
  if (previous?.cache === name && await caches.has(name)) { await cacheStatus(); return; }
  const cache = await caches.open(name);
  try {
    let completed = 0;
    for (let start = 0; start < entries.length; start += 6) {
      await Promise.all(entries.slice(start, start + 6).map(async (entry) => {
        const url = new URL("/" + entry.path, self.location.origin);
        const response = await fetch(url, {cache: "no-store", credentials: "omit"});
        if (!response.ok || response.redirected) throw new Error("读取失败");
        const bytes = await response.arrayBuffer();
        const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map((value) => value.toString(16).padStart(2, "0")).join("");
        if (bytes.byteLength !== entry.size || digest !== entry.sha256) throw new Error("校验失败");
        await cache.put(url, new Response(bytes, {headers: response.headers, status: 200}));
        completed++;
      }));
      await announce({type: "CACHE_PROGRESS", completed, total: entries.length});
    }
    await cache.put("/content-manifest.json", new Response(JSON.stringify(manifest), {headers: {"Content-Type": "application/json"}}));
    const state = await caches.open(STATE_CACHE);
    await state.put(STATE_URL, new Response(JSON.stringify({cache: name, revision: manifest.revision})));
    await announce({type: "CACHE_READY", revision: manifest.revision});
    const obsolete = (await caches.keys()).filter((key) => key.startsWith(PREFIX) && key !== name && key !== previous?.cache);
    await Promise.all(obsolete.map((key) => caches.delete(key)));
  } catch (error) {
    if (name !== previous?.cache) await caches.delete(name);
    throw error;
  }
}
function prepareCache() {
  if (!pending) pending = performCache().catch(async () => { await announce({type: "CACHE_ERROR"}); }).finally(() => { pending = null; });
  return pending;
}
self.addEventListener("install", (event) => event.waitUntil(prepareCache().then(() => self.skipWaiting())));
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("message", (event) => {
  if (event.data?.type === "PREPARE_CACHE") event.waitUntil(prepareCache());
  else if (event.data?.type === "CACHE_STATUS") event.waitUntil(cacheStatus());
});
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  let path;
  try { path = decodeURIComponent(url.pathname); } catch { return; }
  if (event.request.method !== "GET" || url.origin !== self.location.origin || excluded(path)) return;
  event.respondWith((async () => {
    const state = await currentState();
    if (state) {
      const cache = await caches.open(state.cache);
      const saved = await cache.match(path === "/" ? "/index.html" : event.request, {ignoreSearch: true});
      if (saved) return saved;
      if (event.request.mode === "navigate") {
        const offline = await cache.match("/offline.html");
        if (offline) return offline;
      }
    } else {
      // 第一版缓存尚未就绪时允许在线阅读；已提交版本始终整套读取。
      try {
        const response = await fetch(event.request);
        if (response.ok) return response;
      } catch {}
    }
    return new Response("此内容尚未缓存。请启动本地服务后重新打开。", {status: 503, headers: {"Content-Type": "text/plain; charset=utf-8"}});
  })());
});
