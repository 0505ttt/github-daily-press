"use strict";
// 在线阅读不能依赖本机接口，也不能在仓库子目录加载域名根目录的资源。
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../web/pwa.js"), "utf8");
async function application(address, mode) {
  const location = new URL(address), base = new URL(".", location);
  const requests = [], registrations = [], posted = [], intervals = [], actions = new Map(), serviceEvents = new Map();
  const state = {textContent: ""}, install = {}, settings = {}, fullscreen = {};
  let bar;
  const registration = {active: {postMessage(message) { posted.push(message); }}, async update() {}};
  const document = {
    currentScript: {src: new URL("pwa.js", base).href},
    querySelector() { return null; },
    createElement() {
      bar = {
        dataset: {}, innerHTML: "", setAttribute() {}, getBoundingClientRect() { return {height: 40}; },
        addEventListener(kind, callback) { actions.set(kind, callback); },
        querySelector(selector) {
          if (selector === ".gh-app-state") return state;
          if (selector.includes("settings")) return settings;
          if (selector.includes("fullscreen")) return fullscreen;
          return install;
        }
      };
      return bar;
    },
    body: {append() {}, classList: {add() {}}},
    documentElement: {style: {setProperty() {}}}, addEventListener() {}
  };
  const environment = {
    URL, document, location, Response,
    window: {addEventListener() {}, matchMedia() { return {matches: false}; }, location: {reload() {}}},
    navigator: {
      serviceWorker: {
        controller: registration.active, ready: Promise.resolve(registration),
        addEventListener(type, callback) { serviceEvents.set(type, callback); },
        async register(script, options) { registrations.push({script, options}); return registration; }
      }
    },
    setInterval(callback) { intervals.push(callback); }, setTimeout,
    async fetch(input) {
      requests.push(input);
      const url = new URL(input);
      if (url.pathname.endsWith("/site-config.json")) {
        if (mode === null) throw new Error("网络断开");
        return new Response(JSON.stringify({mode, base_path: base.pathname}));
      }
      if (url.pathname.endsWith("/api/status")) return new Response(JSON.stringify({job: {running: false}}));
      throw new Error("意外的请求 " + input);
    }
  };
  vm.runInContext(source, vm.createContext(environment));
  await new Promise(setImmediate);
  return {
    bar, state, requests, registrations, posted, intervals,
    async click(action) { await actions.get("click")({target: {closest() { return {dataset: {action}}; }}}); },
    notify(data, scriptURL = new URL('sw.js', base).href) { serviceEvents.get("message")({data, source: {scriptURL}}); }
  };
}
(async () => {
  for (const mode of ["hosted", "local", null]) {
    const hosted = await application("https://reader.example/github-daily-press/pwa.js", mode);
    assert.equal(hosted.bar.dataset.mode, "hosted", "公网不能通过配置开启本机操作");
    assert.equal(hosted.bar.innerHTML.includes('data-action="sync"'), false);
    assert.equal(hosted.bar.innerHTML.includes('data-action="settings"'), false);
    assert.equal(hosted.bar.innerHTML.includes('data-action="refresh"'), true);
    assert.equal(hosted.registrations[0].script, "https://reader.example/github-daily-press/sw.js");
    assert.equal(hosted.registrations[0].options.scope, "https://reader.example/github-daily-press/");
    await hosted.click("refresh");
    await hosted.click("sync");
    hosted.intervals.forEach((callback) => callback());
    assert.ok(hosted.requests.every((url) => !new URL(url).pathname.includes("/api/")), "加载、定时检查及按钮点击都不能请求本机接口");
    assert.ok(hosted.posted.some((message) => message.type === "PREPARE_CACHE"));
    const previousState = hosted.state.textContent;
    hosted.notify({type: "CACHE_READY", revision: "foreign"}, 'https://reader.example/sw.js');
    assert.equal(hosted.state.textContent, previousState, "忽略同域其他应用的缓存广播");
    hosted.notify({type: "CACHE_READY", revision: "a", generated_at: "2026-10-23T08:30:00+08:00"});
    assert.ok(hosted.state.textContent.includes("已可离线阅读"));
    assert.ok(hosted.state.textContent.includes("2026-10-23 08:30"));
    hosted.notify({type: "CACHE_READY", revision: "b"});
    assert.equal(hosted.state.textContent, "新内容已缓存，刷新页面即可阅读。");
  }
  const local = await application("http://127.0.0.1:8765/pwa.js", "local");
  assert.equal(local.bar.dataset.mode, "local");
  assert.ok(local.bar.innerHTML.includes('data-action="settings"'));
  assert.ok(local.requests.includes("http://127.0.0.1:8765/api/status"));
  const preview = await application("http://localhost:8765/github-daily-press/pwa.js", "hosted");
  assert.equal(preview.bar.dataset.mode, "hosted", "本机预览线上产物仍应使用只读模式");
  assert.ok(preview.requests.every((url) => !new URL(url).pathname.includes("/api/")));
  console.log("PWA 在线阅读、子目录资源与本机接口隔离检查通过。");
})().catch((error) => { console.error(error); process.exitCode = 1; });
