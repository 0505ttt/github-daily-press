"use strict";
// 不依赖浏览器插件的 Service Worker 版本一致性回归。
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {webcrypto, createHash} = require("node:crypto");
const origin = "http://127.0.0.1:8765";
const stores = new Map();
const handlers = new Map();
const key = (input) => new URL(typeof input === "string" ? input : input.url || input.href, origin).href;
const caches = {
  async open(name) {
    if (!stores.has(name)) stores.set(name, new Map());
    const store = stores.get(name);
    return {
      async put(input, response) { store.set(key(input), response.clone()); },
      async match(input) { return store.get(key(input))?.clone(); }
    };
  },
  async keys() { return [...stores.keys()]; },
  async has(name) { return stores.has(name); },
  async delete(name) { return stores.delete(name); }
};
let manifest;
let network = {};
let failScript = false;
const environment = {
  URL, Request, Response, crypto: webcrypto, caches, console,
  self: {
    location: {origin},
    clients: {async matchAll() { return []; }, async claim() {}},
    async skipWaiting() {},
    addEventListener(type, callback) { handlers.set(type, callback); }
  },
  async fetch(input) {
    const pathname = new URL(key(input)).pathname;
    if (pathname === "/content-manifest.json") return new Response(JSON.stringify(manifest));
    if (pathname === "/pwa.js" && failScript) return new Response("暂不可用", {status: 503});
    return new Response(network[pathname] || "未找到", {status: pathname in network ? 200 : 404});
  }
};
const context = vm.createContext(environment);
vm.runInContext(fs.readFileSync(path.join(__dirname, "../web/sw.js"), "utf8"), context);
function version(revision) {
  network = {"/index.html": "页面-" + revision, "/pwa.js": "脚本-" + revision};
  manifest = {revision, files: Object.entries(network).map(([file, value]) => ({
    path: file.slice(1), size: Buffer.byteLength(value), sha256: createHash("sha256").update(value).digest("hex")
  }))};
}
async function read(resource) {
  let promise;
  handlers.get("fetch")({request: new Request(origin + resource), respondWith(value) { promise = value; }});
  return (await promise).text();
}
(async () => {
  version("a");
  await vm.runInContext("performCache()", context);
  version("b"); failScript = true;
  await assert.rejects(vm.runInContext("performCache()", context));
  assert.equal(await read("/index.html"), "页面-a", "更新失败时不能混用新版页面");
  assert.equal(await read("/pwa.js"), "脚本-a", "旧版脚本与页面保持一致");
  failScript = false;
  await vm.runInContext("performCache()", context);
  assert.equal(await read("/index.html"), "页面-b");
  assert.equal(await read("/pwa.js"), "脚本-b");
  assert.equal(vm.runInContext("excluded('/api/config') && excluded('/settings.html') && excluded('/settings.js')", context), true);
  console.log("Service Worker 版本一致性与私密路由隔离检查通过。");
})().catch((error) => { console.error(error); process.exitCode = 1; });
