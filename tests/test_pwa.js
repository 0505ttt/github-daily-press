"use strict";
// 阅读工具必须可收起；公网操作不能接触本机，断连时设置不能跳到错误页。
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../web/pwa.js"), "utf8");
const json = (value, status = 200) => new Response(JSON.stringify(value), {status, headers: {"Content-Type": "application/json"}});
async function application(address, mode, native = false) {
  const location = new URL(address), base = new URL(".", location);
  const requests = [], registrations = [], posted = [], intervals = [], navigations = [];
  const actions = new Map(), serviceEvents = new Map(), documentEvents = new Map(), windowEvents = new Map();
  const state = {textContent: ""}, panel = {hidden: true}, guidance = {hidden: true, textContent: ""};
  const buttons = Object.fromEntries(["tools", "install", "settings", "fullscreen", "sync", "refresh"].map((action) => [action, {
    dataset: {action}, attrs: {}, disabled: false, focused: false,
    setAttribute(name, value) { this.attrs[name] = value; }, focus() { this.focused = true; }
  }]));
  buttons.tools.attrs["aria-expanded"] = "false";
  let bar, statusMode = "online", aborts = 0;
  const registration = {active: {postMessage(message) { posted.push(message); }}, async update() {}};
  const document = {
    currentScript: {src: new URL("pwa.js", base).href}, querySelector() { return null; },
    createElement() {
      bar = {
        dataset: {}, innerHTML: "", setAttribute() {},
        contains(target) { return Object.values(buttons).includes(target) || target === panel; },
        addEventListener(kind, callback) { actions.set(kind, callback); },
        querySelector(selector) {
          if (selector === ".gh-app-state") return state;
          if (selector === ".gh-app-panel") return panel;
          if (selector === ".gh-app-guidance") return guidance;
          return buttons[selector.match(/data-action="(\w+)"/)[1]];
        }
      };
      return bar;
    },
    body: {append() {}, classList: {add() {}}}, documentElement: {},
    addEventListener(type, callback) { documentEvents.set(type, callback); }
  };
  const environment = {
    URL, document, location, Response, AbortController,
    window: {
      pywebview: native ? {} : undefined,
      addEventListener(type, callback) { windowEvents.set(type, callback); }, matchMedia() { return {matches: false}; },
      location: {reload() {}, assign(address) { navigations.push(address); }}
    },
    navigator: {serviceWorker: {
      controller: registration.active, ready: Promise.resolve(registration),
      addEventListener(type, callback) { serviceEvents.set(type, callback); },
      async register(script, options) { registrations.push({script, options}); return registration; }
    }},
    setInterval(callback) { intervals.push(callback); },
    setTimeout(callback, milliseconds) { return setTimeout(callback, milliseconds === 3000 ? 15 : milliseconds); }, clearTimeout,
    async fetch(input, options) {
      requests.push({url: input, options});
      const url = new URL(input);
      if (url.pathname.endsWith("/site-config.json")) {
        if (mode === null) throw new Error("网络断开");
        return json({mode, base_path: base.pathname});
      }
      if (url.pathname.endsWith("/api/status")) {
        if (statusMode === "offline") throw new Error("ERR_CONNECTION_REFUSED");
        if (statusMode === "html") return new Response("<html>代理错误</html>", {headers: {"Content-Type": "text/html"}});
        if (statusMode === "invalid") return json({job: {running: false}});
        if (statusMode === "timeout") return new Promise((resolve, reject) => {
          options.signal.addEventListener("abort", () => { aborts++; reject(new Error("超时")); });
        });
        if (statusMode === "body-timeout") return {ok: true, headers: new Headers({"Content-Type": "application/json"}),
          json: () => new Promise((resolve, reject) => {
            options.signal.addEventListener("abort", () => { aborts++; reject(new Error("响应超时")); });
          })};
        return json({online: true, job: {running: false}});
      }
      throw new Error("意外的请求 " + input);
    }
  };
  vm.runInContext(source, vm.createContext(environment));
  await new Promise(setImmediate);
  return {
    bar, state, panel, guidance, buttons, requests, registrations, posted, intervals, navigations,
    get aborts() { return aborts; }, setStatus(value) { statusMode = value; },
    async click(action) { await actions.get("click")({target: {closest() { return buttons[action]; }}}); },
    outside() { documentEvents.get("click")({target: {}}); },
    escape() { let prevented = false; documentEvents.get("keydown")({key: "Escape", preventDefault() { prevented = true; }}); return prevented; },
    nativeReady() { windowEvents.get("pywebviewready")(); },
    notify(data, scriptURL = new URL("sw.js", base).href) { serviceEvents.get("message")({data, source: {scriptURL}}); }
  };
}
(async () => {
  let checks = 0;
  for (const mode of ["hosted", "local", null]) {
    const hosted = await application("https://reader.example/github-daily-press/pwa.js", mode);
    assert.equal(hosted.bar.dataset.mode, "hosted", "公网不能通过配置开启本机操作");
    assert.equal(hosted.bar.innerHTML.includes('data-action="sync"'), false);
    assert.equal(hosted.bar.innerHTML.includes('data-action="settings"'), false);
    assert.equal(hosted.bar.innerHTML.includes('data-action="refresh"'), true);
    assert.equal(hosted.registrations[0].script, "https://reader.example/github-daily-press/sw.js");
    assert.equal(hosted.registrations[0].options.scope, "https://reader.example/github-daily-press/");
    await hosted.click("refresh"); await hosted.click("sync"); await hosted.click("settings");
    hosted.intervals.forEach((callback) => callback());
    assert.ok(hosted.requests.every(({url}) => !new URL(url).pathname.includes("/api/")), "加载、定时检查及按钮点击都不能请求本机接口");
    assert.equal(hosted.navigations.length, 0);
    assert.ok(hosted.posted.some((message) => message.type === "PREPARE_CACHE"));
    const previousState = hosted.state.textContent;
    hosted.notify({type: "CACHE_READY", revision: "foreign"}, "https://reader.example/sw.js");
    assert.equal(hosted.state.textContent, previousState, "忽略同域其他应用的缓存广播");
    hosted.notify({type: "CACHE_READY", revision: "a", generated_at: "2026-10-23T08:30:00+08:00"});
    assert.ok(hosted.state.textContent.includes("已可离线阅读"));
    assert.ok(hosted.state.textContent.includes("2026-10-23 08:30"));
    hosted.notify({type: "CACHE_READY", revision: "b"});
    assert.equal(hosted.state.textContent, "新内容已缓存，刷新页面即可阅读。");
    checks++;
  }
  const local = await application("http://127.0.0.1:8765/pwa.js", "local");
  assert.equal(local.bar.dataset.mode, "local");
  assert.ok(local.bar.innerHTML.includes('<button type="button" data-action="settings">'));
  assert.ok(local.requests.some(({url}) => url === "http://127.0.0.1:8765/api/status"));
  assert.equal(local.panel.hidden, true, "首次打开只有紧凑工具按钮");
  await local.click("tools");
  assert.equal(local.panel.hidden, false); assert.equal(local.buttons.tools.attrs["aria-expanded"], "true");
  await local.click("tools");
  assert.equal(local.panel.hidden, true); checks++;
  await local.click("tools"); local.outside();
  assert.equal(local.panel.hidden, true); checks++;
  await local.click("tools"); assert.equal(local.escape(), true);
  assert.equal(local.panel.hidden, true); assert.equal(local.buttons.tools.focused, true);
  assert.equal(local.buttons.tools.attrs["aria-expanded"], "false"); checks++;
  await local.click("settings");
  assert.deepEqual(local.navigations, ["http://127.0.0.1:8765/settings.html"]);
  assert.equal(local.buttons.settings.disabled, false); checks++;
  for (const failure of ["offline", "html", "invalid", "timeout", "body-timeout"]) {
    const failed = await application("http://127.0.0.1:8765/pwa.js", "local");
    failed.setStatus(failure); await failed.click("settings");
    assert.equal(failed.navigations.length, 0, "未连接或不是本项目服务时禁止导航");
    assert.equal(failed.panel.hidden, false); assert.equal(failed.guidance.hidden, false);
    assert.ok(failed.guidance.textContent.includes("重新打开桌面应用"));
    assert.ok(!failed.guidance.textContent.includes("ERR_CONNECTION_REFUSED"));
    assert.equal(failed.buttons.settings.disabled, false);
    if (failure.endsWith("timeout")) assert.equal(failed.aborts, 1, "连接探测和响应体读取都具有期限");
    failed.setStatus("online"); await failed.click("settings");
    assert.equal(failed.navigations.length, 1, "恢复服务后可以重新进入设置");
    assert.ok(failed.requests.every(({options}) => options.cache === "no-store"));
    checks++;
  }
  const preview = await application("http://localhost:8765/github-daily-press/pwa.js", "hosted");
  assert.equal(preview.bar.dataset.mode, "hosted", "本机预览线上产物仍应使用只读模式");
  assert.ok(preview.requests.every(({url}) => !new URL(url).pathname.includes("/api/"))); checks++;
  const native = await application("http://127.0.0.1:8765/pwa.js", "local", true);
  assert.equal(native.buttons.install.hidden, true);
  local.nativeReady(); assert.equal(local.buttons.install.hidden, true); checks++;
  console.log(`PWA ${checks} 个场景通过：工具收纳、键盘焦点、设置断连恢复、网络期限、原生窗口及线上隔离。`);
})().catch((error) => { console.error(error); process.exitCode = 1; });
