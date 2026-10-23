"use strict";
// 同一域名可以部署多个项目，每套缓存和通知都限定在自己的应用目录。
const BASE_URL = new URL(self.registration.scope);
const SCOPE_KEY = encodeURIComponent(BASE_URL.pathname);
const STATE_CACHE = "gh-daily-state-v2-" + SCOPE_KEY;
const STATE_URL = new URL("__gh_daily_cache_state__", BASE_URL).href;
const PREFIX = "gh-daily-content-v2-" + SCOPE_KEY + "-";
const MAX_FILES = 2000;
const MAX_TOTAL = 64 * 1024 * 1024;
const NETWORK_TIMEOUT = 30000;
let pending = null;

function scopedPath(url) {
  if (url.origin !== BASE_URL.origin || !url.pathname.startsWith(BASE_URL.pathname)) return null;
  try { return "/" + decodeURIComponent(url.pathname.slice(BASE_URL.pathname.length)); }
  catch { return null; }
}
function excluded(path) {
  return path.startsWith("/api/") || path === "/api" || path === "/settings.html" || path === "/settings.js" || path === "/sw.js";
}
function safePath(path) {
  if (typeof path !== "string" || !path || path.length > 500 || /[\\%:#?]/.test(path) || path.startsWith("/")) return false;
  return path.split("/").every((part) => part && !part.startsWith("."));
}
async function announce(message) {
  const pages = await self.clients.matchAll({includeUncontrolled: true});
  pages.forEach((page) => {
    if (page.url && scopedPath(new URL(page.url)) !== null) page.postMessage(message);
  });
}
async function currentState() {
  const state = await caches.open(STATE_CACHE);
  const response = await state.match(STATE_URL);
  return response ? response.json() : null;
}
async function cacheStatus() {
  const state = await currentState();
  if (state && state.cache?.startsWith(PREFIX) && await caches.has(state.cache)) {
    await announce({type: "CACHE_READY", revision: state.revision, generated_at: state.generated_at || ""});
  }
}
async function removeOldVersions(current) {
  const obsolete = (await caches.keys()).filter((key) => key.startsWith(PREFIX) && key !== current);
  await Promise.all(obsolete.map((key) => caches.delete(key)));
}
async function readResource(url, readBody) {
  // 超时覆盖响应头和完整响应体；单个连接卡住时不能无限阻塞整套缓存。
  for (let attempt = 0; attempt < 2; attempt++) {
    const controller = new AbortController();
    let timer;
    const deadline = new Promise((resolve, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        reject(new Error("读取超时"));
      }, NETWORK_TIMEOUT);
    });
    try {
      return await Promise.race([
        (async () => {
          const response = await fetch(url, {cache: "no-store", credentials: "omit", signal: controller.signal});
          if (!response.ok || response.redirected) throw new Error("读取失败");
          return {response, body: await readBody(response)};
        })(),
        deadline
      ]);
    } catch (error) {
      controller.abort();
      if (attempt === 1) throw error;
    } finally {
      clearTimeout(timer);
    }
  }
}
async function performCache() {
  const manifestUrl = new URL("content-manifest.json", BASE_URL);
  const {body: manifest} = await readResource(manifestUrl, (response) => response.json());
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
  if (previous?.cache === name && await caches.has(name)) {
    await removeOldVersions(name);
    await cacheStatus();
    return;
  }
  const cache = await caches.open(name);
  let committed = false;
  try {
    let completed = 0;
    for (let start = 0; start < entries.length; start += 6) {
      await Promise.all(entries.slice(start, start + 6).map(async (entry) => {
        const url = new URL(entry.path, BASE_URL);
        const {response, body: bytes} = await readResource(url, (response) => response.arrayBuffer());
        const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map((value) => value.toString(16).padStart(2, "0")).join("");
        if (bytes.byteLength !== entry.size || digest !== entry.sha256) throw new Error("校验失败");
        await cache.put(url, new Response(bytes, {headers: response.headers, status: 200}));
        completed++;
      }));
      await announce({type: "CACHE_PROGRESS", completed, total: entries.length});
    }
    await cache.put(manifestUrl, new Response(JSON.stringify(manifest), {headers: {"Content-Type": "application/json"}}));
    const generatedAt = typeof manifest.generated_at === "string" ? manifest.generated_at.slice(0, 64) : "";
    const state = await caches.open(STATE_CACHE);
    await state.put(STATE_URL, new Response(JSON.stringify({cache: name, revision: manifest.revision, generated_at: generatedAt})));
    committed = true;
    // 新版已完整校验并提交后删除本应用旧版，避免已清理的历史正文继续留在缓存。
    await removeOldVersions(name);
    await announce({type: "CACHE_READY", revision: manifest.revision, generated_at: generatedAt});
  } catch (error) {
    if (!committed && name !== previous?.cache) await caches.delete(name);
    throw error;
  }
}
function prepareCache() {
  if (!pending) pending = performCache().then(() => true).catch(async () => { await announce({type: "CACHE_ERROR"}); return false; }).finally(() => { pending = null; });
  return pending;
}
self.addEventListener("install", (event) => event.waitUntil(prepareCache().then((complete) => {
  // 新 Worker 无法准备完整缓存时安装失败，让浏览器保留旧 Worker 和旧缓存。
  if (!complete) throw new Error("离线版本未准备完成，保留现有 Worker。");
  return self.skipWaiting();
})));
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("message", (event) => {
  if (!event.source?.url || scopedPath(new URL(event.source.url)) === null) return;
  if (event.data?.type === "PREPARE_CACHE") event.waitUntil(prepareCache());
  else if (event.data?.type === "CACHE_STATUS") event.waitUntil(cacheStatus());
});
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const path = scopedPath(url);
  if (event.request.method !== "GET" || path === null || excluded(path)) return;
  event.respondWith((async () => {
    const state = await currentState();
    if (state?.cache?.startsWith(PREFIX)) {
      const cache = await caches.open(state.cache);
      const saved = await cache.match(path === "/" ? new URL("index.html", BASE_URL) : event.request, {ignoreSearch: true});
      if (saved) return saved;
      if (event.request.mode === "navigate") {
        const offline = await cache.match(new URL("offline.html", BASE_URL));
        if (offline) return offline;
      }
    } else {
      // 第一版缓存尚未就绪时允许在线阅读；已提交版本始终整套读取。
      try {
        const response = await fetch(event.request);
        if (response.ok) return response;
      } catch {}
    }
    return new Response("此内容尚未缓存。请恢复网络或本地服务后重新打开。", {status: 503, headers: {"Content-Type": "text/plain; charset=utf-8"}});
  })());
});
