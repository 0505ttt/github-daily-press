"use strict";
// 本地设置的连接恢复不得回显敏感响应，也不能自动重放收费请求。
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../web/settings.js"), "utf8");
const json = (value, status = 200) => new Response(JSON.stringify(value), {status, headers: {"Content-Type": "application/json"}});
const config = {provider: "cloud", base_url: "https://model.example/v1", model: "example-model", timeout: 30, max_tokens: 800, source_repo: "", api_key_set: true};
const settle = async () => { for (let count = 0; count < 8; count++) await new Promise(setImmediate); };
async function application(initialFailure = null) {
  const requests = [], events = new Map(), fields = new Map(), elements = new Map();
  let failure = initialFailure, tokenNumber = 0, aborts = 0;
  const element = () => ({value: "", textContent: "", dataset: {}, handlers: new Map(), addEventListener(kind, callback) { this.handlers.set(kind, callback); }});
  for (const name of ["provider", "base_url", "model", "timeout", "max_tokens", "source_repo", "api_key", "clear_api_key"]) fields.set(name, element());
  for (const name of ["status", "key-field", "clear-key-field", "url-hint", "test-connection", "sync-content", "update-content"]) elements.set(name, element());
  const form = element();
  form.elements = {namedItem(name) { return fields.get(name); }};
  form.reportValidity = () => true;
  elements.set("settings-form", form);
  const buttons = ["test-connection", "sync-content", "update-content"].map((name) => elements.get(name));
  const document = {querySelector(selector) { return elements.get(selector.slice(1)); }, querySelectorAll() { return buttons; }};
  vm.runInContext(source, vm.createContext({
    document, window: {addEventListener(kind, callback) { events.set(kind, callback); }}, AbortController,
    setTimeout(callback, delay) { return setTimeout(callback, delay >= 10000 ? 15 : 0); }, clearTimeout,
    async fetch(input, options) {
      requests.push({input, options});
      if (failure === "initial-offline" || (input === "/api/test-connection" && failure === "offline")) throw new Error("ERR_CONNECTION_REFUSED private-response-marker");
      if (input === "/api/session") return json({token: "session-" + (++tokenNumber)});
      if (input === "/api/config") {
        if (failure === "config-invalid") return json({});
        return json(config);
      }
      if (input === "/api/test-connection") {
        if (failure === "html") return new Response("<html>private-response-marker</html>", {headers: {"Content-Type": "text/html"}});
        if (failure === "malformed") return new Response("private-response-marker", {headers: {"Content-Type": "application/json"}});
        if (failure === "bad-shape") return json([]);
        if (failure === "bad-success") return json({message: "private-response-marker"});
        if (failure === "401" || failure === "403" || failure === "400") return json({error: "private-response-marker"}, Number(failure));
        if (failure === "timeout") return new Promise((resolve, reject) => {
          options.signal.addEventListener("abort", () => { aborts++; reject(new Error("等待超时")); });
        });
        if (failure === "body-timeout") return {ok: true, status: 200, headers: new Headers({"Content-Type": "application/json"}),
          json: () => new Promise((resolve, reject) => {
            options.signal.addEventListener("abort", () => { aborts++; reject(new Error("响应超时")); });
          })};
        return json({ok: true, message: "连接成功，JSON 输出校验通过。"});
      }
      throw new Error("意外路径 " + input);
    }
  }));
  await settle();
  return {
    requests, fields, form, status: elements.get("status"), buttons,
    get aborts() { return aborts; }, setFailure(value) { failure = value; },
    async test() { await elements.get("test-connection").handlers.get("click")(); await settle(); },
    async save() { form.handlers.get("submit")({preventDefault() {}}); await settle(); },
    async emit(kind, argument = {}) { events.get(kind)(argument); await settle(); }
  };
}
(async () => {
  let checks = 0;
  const normal = await application();
  assert.ok(normal.status.textContent.includes("本地服务已连接"));
  assert.equal(normal.fields.get("api_key").value, "");
  normal.fields.get("api_key").value = "test-only-value";
  await normal.test();
  assert.ok(normal.status.textContent.includes("JSON 输出校验通过"));
  const posted = normal.requests.find(({input}) => input === "/api/test-connection");
  assert.equal(posted.options.headers["X-GH-Daily-Token"], "session-1");
  assert.equal(JSON.parse(posted.options.body).api_key, "test-only-value");
  assert.ok(normal.requests.every(({options}) => options.cache === "no-store" && options.credentials === "same-origin"));
  await normal.save(); assert.equal(normal.fields.get("api_key").value, ""); checks++;
  for (const failure of ["offline", "html", "malformed", "bad-shape", "bad-success", "400", "timeout", "body-timeout"]) {
    const app = await application(); app.setFailure(failure); await app.test();
    assert.equal(app.status.dataset.error, "true");
    assert.equal(app.status.textContent.includes("private-response-marker"), false, "原始接口内容不得进入提示");
    assert.equal(app.status.textContent.includes("ERR_CONNECTION_REFUSED"), false);
    assert.equal(app.requests.filter(({input}) => input === "/api/test-connection").length, 1, "失败不自动重发模型测试");
    assert.ok(app.buttons.every((button) => !button.disabled), "失败后可以手动重试");
    if (failure.endsWith("timeout")) assert.equal(app.aborts, 1);
    checks++;
  }
  for (const status of ["401", "403"]) {
    const app = await application(); app.setFailure(status); await app.test();
    assert.ok(app.status.textContent.includes("会话已更新"));
    assert.equal(app.requests.filter(({input}) => input === "/api/session").length, 2);
    assert.equal(app.requests.filter(({input}) => input === "/api/test-connection").length, 1);
    app.setFailure(null); await app.test();
    const retry = app.requests.filter(({input}) => input === "/api/test-connection")[1];
    assert.equal(retry.options.headers["X-GH-Daily-Token"], "session-2");
    assert.ok(app.status.textContent.includes("连接成功")); checks++;
  }
  const disconnected = await application("initial-offline");
  assert.ok(disconnected.status.textContent.includes("重新打开桌面应用"));
  disconnected.setFailure(null); await disconnected.test();
  assert.ok(disconnected.status.textContent.includes("连接成功")); checks++;
  const invalid = await application("config-invalid");
  assert.ok(invalid.status.textContent.includes("配置响应不完整")); checks++;
  normal.fields.get("api_key").value = "unsaved-test-value";
  await normal.emit("pagehide"); assert.equal(normal.fields.get("api_key").value, "");
  await normal.emit("pageshow", {persisted: true});
  assert.ok(normal.status.textContent.includes("未保留未保存的密钥")); checks++;
  console.log(`设置 ${checks} 个场景通过：连接恢复、响应校验、安全错误、会话更新不重放、密钥清除及缓存隔离。`);
})().catch((error) => { console.error(error); process.exitCode = 1; });
