"use strict";
// 不依赖浏览器插件的离线版本、私密路由与 Pages 子目录回归。
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {webcrypto, createHash} = require("node:crypto");
const origin = "https://reader.example";
const source = fs.readFileSync(path.join(__dirname, "../web/sw.js"), "utf8");
const stores = new Map();
const key = (input) => new URL(typeof input === "string" ? input : input.url || input.href, origin).href;
const caches = {
  async open(name) {
    if (!stores.has(name)) stores.set(name, new Map());
    const store = stores.get(name);
    return {
      async put(input, response) { store.set(key(input), response.clone()); },
      async match(input, options = {}) {
        if (!options.ignoreSearch) return store.get(key(input))?.clone();
        const target = new URL(key(input)); target.search = "";
        for (const [saved, response] of store) {
          const candidate = new URL(saved); candidate.search = "";
          if (target.href === candidate.href) return response.clone();
        }
      }
    };
  },
  async keys() { return [...stores.keys()]; },
  async has(name) { return stores.has(name); },
  async delete(name) { return stores.delete(name); }
};
function application(basePath) {
  const handlers = new Map(), requests = [], ownMessages = [], otherMessages = [];
  const activeTimers = new Set();
  let manifest, network = {}, failScript = false, hang = null, fastTimeout = false, aborts = 0, skipped = 0;
  function untilAborted(signal) {
    return new Promise((resolve, reject) => {
      if (signal.aborted) { reject(new Error("请求已中止")); return; }
      signal.addEventListener("abort", () => { aborts++; reject(new Error("请求已中止")); }, {once: true});
    });
  }
  const environment = {
    URL, Request, Response, AbortController, crypto: webcrypto, caches, console,
    setTimeout(callback, milliseconds) {
      const timer = setTimeout(() => { activeTimers.delete(timer); callback(); }, fastTimeout ? 10 : milliseconds);
      activeTimers.add(timer);
      return timer;
    },
    clearTimeout(timer) { clearTimeout(timer); activeTimers.delete(timer); },
    self: {
      location: {origin}, registration: {scope: origin + basePath},
      clients: {
        async matchAll() { return [
          {url: origin + basePath + "index.html", postMessage(message) { ownMessages.push(message); }},
          {url: origin + "/outside/index.html", postMessage(message) { otherMessages.push(message); }},
          {url: "https://other.example" + basePath, postMessage(message) { otherMessages.push(message); }}
        ]; },
        async claim() {}
      },
      async skipWaiting() { skipped++; }, addEventListener(type, callback) { handlers.set(type, callback); }
    },
    async fetch(input, options = {}) {
      const pathname = decodeURI(new URL(key(input)).pathname);
      requests.push(pathname);
      if (hang?.path === pathname && hang.phase === "fetch") return untilAborted(options.signal);
      if (hang?.path === pathname && hang.phase === "body") return {
        ok: true, redirected: false, headers: new Headers(),
        arrayBuffer() { return untilAborted(options.signal); },
        json() { return untilAborted(options.signal); }
      };
      if (pathname === basePath + "content-manifest.json") return new Response(JSON.stringify(manifest));
      if (pathname === basePath + "pwa.js" && failScript) return new Response("暂不可用", {status: 503});
      return new Response(network[pathname] || "未找到", {status: pathname in network ? 200 : 404});
    }
  };
  const context = vm.createContext(environment);
  vm.runInContext(source, context);
  return {
    requests, ownMessages, otherMessages, handlers, activeTimers,
    run(code) { return vm.runInContext(code, context); },
    setFail(value) { failScript = value; },
    hang(path, phase) { hang = {path: basePath + path, phase}; fastTimeout = true; },
    get aborts() { return aborts; },
    get skipped() { return skipped; },
    setManifest(value) { manifest = value; },
    version(revision, label = revision) {
      network = Object.fromEntries(Object.entries({
        "index.html": "页面-" + label, "pwa.js": "脚本-" + label,
        "offline.html": "离线提示-" + label, "GitHub项目分析/日报.html": "中文路径-" + label,
        "settings.html": "不应缓存设置", "settings.js": "不应缓存私密脚本", "api/config": "不应缓存接口"
      }).map(([file, value]) => [basePath + file, value]));
      manifest = {revision, generated_at: "2026-10-23T08:30:00+08:00", files: Object.entries(network).map(([file, value]) => ({
        path: file.slice(basePath.length), size: Buffer.byteLength(value), sha256: createHash("sha256").update(value).digest("hex")
      }))};
      return manifest;
    },
    async read(resource, mode = "cors") {
      let promise;
      handlers.get("fetch")({request: {url: origin + resource, method: "GET", mode}, respondWith(value) { promise = value; }});
      return promise ? (await promise).text() : null;
    }
  };
}
(async () => {
  const root = application("/");
  root.version("a"); await root.run("performCache()");
  root.version("b"); root.setFail(true);
  await assert.rejects(root.run("performCache()"));
  assert.equal(await root.read("/index.html"), "页面-a", "更新失败时不能混用新版页面");
  assert.equal(await root.read("/pwa.js"), "脚本-a", "旧版脚本与页面保持一致");
  root.setFail(false); await root.run("performCache()");
  assert.equal(await root.read("/index.html"), "页面-b");
  assert.equal(await root.read("/pwa.js"), "脚本-b");
  assert.equal(await root.read("/api/config"), null);
  assert.equal(await root.read("/settings.html"), null);

  const hosted = application("/github-daily-press/");
  hosted.version("b", "独立站"); await hosted.run("performCache()");
  assert.equal(await hosted.read("/github-daily-press/"), "页面-独立站", "子目录首页应命中 index");
  assert.equal(await hosted.read("/github-daily-press/pwa.js?v=1"), "脚本-独立站");
  assert.equal(await hosted.read("/github-daily-press/" + encodeURI("GitHub项目分析/日报.html")), "中文路径-独立站");
  assert.equal(await hosted.read("/github-daily-press/不存在.html", "navigate"), "离线提示-独立站");
  assert.equal(await hosted.read("/index.html"), null, "不能拦截仓库子目录以外的请求");
  assert.equal(await hosted.read("/github-daily-press-sibling/index.html"), null);
  assert.equal(await hosted.read("/github-daily-press/settings.js"), null);
  assert.equal(await hosted.read("/github-daily-press/api/config"), null);
  assert.ok(hosted.requests.every((resource) => resource.startsWith("/github-daily-press/") && !resource.includes("/api/") && !resource.includes("settings")));
  assert.equal(hosted.otherMessages.length, 0, "不能向其他站点窗口广播缓存状态");
  assert.ok(hosted.ownMessages.some((item) => item.type === "CACHE_READY" && item.generated_at.startsWith("2026-10-23")));
  assert.equal(await root.read("/index.html"), "页面-b", "相同 revision 不得复用其他目录的缓存");

  for (const revision of ["c", "d", "e"]) { hosted.version(revision); await hosted.run("performCache()"); }
  assert.equal(await root.read("/pwa.js"), "脚本-b", "子目录清理旧版本不能删除根目录缓存");
  const unsafe = hosted.version("unsafe"); unsafe.files[0].path = "../index.html";
  await assert.rejects(hosted.run("performCache()"));
  assert.equal(await hosted.read("/github-daily-press/index.html"), "页面-e");
  let handled = false;
  hosted.handlers.get("message")({source: {url: origin + "/outside/"}, data: {type: "PREPARE_CACHE"}, waitUntil() { handled = true; }});
  assert.equal(handled, false, "不能接受其他目录窗口的缓存指令");
  // 从旧版无 scope 命名迁移时，安装失败不能激活一个看不见旧缓存的 Worker。
  const legacy = await caches.open('gh-daily-content-legacy');
  await legacy.put(origin + '/legacy/index.html', new Response('旧版仍可阅读'));
  const upgrade = application('/legacy/');
  upgrade.version('new'); upgrade.setFail(true);
  let installation;
  upgrade.handlers.get('install')({waitUntil(promise) { installation = promise; }});
  await assert.rejects(installation, /未准备完成/, "缓存失败必须拒绝新 Worker 的安装");
  assert.equal(await (await legacy.match(origin + '/legacy/index.html')).text(), '旧版仍可阅读');
  for (const [resource, phase] of [
    ["content-manifest.json", "fetch"], ["content-manifest.json", "body"],
    ["pwa.js", "fetch"], ["pwa.js", "body"]
  ]) {
    const stalled = application('/stalled-' + resource.split('.')[0] + '-' + phase + '/');
    stalled.version('stable'); await stalled.run('performCache()');
    stalled.ownMessages.length = 0;
    stalled.version('unfinished'); stalled.hang(resource, phase);
    const previousRequests = stalled.requests.length;
    let result;
    stalled.handlers.get('install')({waitUntil(promise) { result = promise; }});
    await assert.rejects(result, /未准备完成/, '响应头或响应体超时必须使新 Worker 安装失败');
    const attempts = stalled.requests.slice(previousRequests).filter((request) => request.endsWith('/' + resource));
    assert.equal(attempts.length, 2, '每个超时资源最多尝试两次');
    assert.equal(stalled.aborts, 2, '两次超时均须中止网络请求或响应体读取');
    assert.equal(stalled.skipped, 0, '缓存不完整时不能激活新 Worker');
    assert.equal(stalled.ownMessages.some((message) => message.type === 'CACHE_READY'), false, '不能误报新版本已可离线阅读');
    assert.equal(await stalled.read(stalled.requests[0].replace('content-manifest.json', 'index.html')), '页面-stable', '超时后旧版本仍可阅读');
    assert.equal(stalled.activeTimers.size, 0, '成功、失败和超时路径均须清除 deadline timer');
  }
  assert.equal(root.activeTimers.size, 0);
  assert.equal(hosted.activeTimers.size, 0);
  console.log("Service Worker 版本一致性、私密路由与 Pages 子目录隔离检查通过。");
})().catch((error) => { console.error(error); process.exitCode = 1; });
