"use strict";
(() => {
  const form = document.querySelector("#settings-form");
  const status = document.querySelector("#status");
  let token = "";
  let busy = false;
  const field = (name) => form.elements.namedItem(name);
  function say(message, error = false) {
    status.textContent = message;
    status.dataset.error = String(error);
  }
  function setBusy(value) {
    busy = value;
    document.querySelectorAll("button").forEach((button) => { button.disabled = value; });
  }
  async function request(path, payload) {
    const options = {cache: "no-store", credentials: "same-origin"};
    if (payload !== undefined) {
      options.method = "POST";
      options.headers = {"Content-Type": "application/json", "X-GH-Daily-Token": token};
      options.body = JSON.stringify(payload);
    }
    let response;
    try { response = await fetch(path, options); }
    catch { throw new Error("本地服务未连接，请先启动服务。已缓存的杂志仍可阅读。"); }
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "本地操作未完成。");
    return result;
  }
  function providerHint() {
    const local = field("provider").value === "ollama";
    document.querySelector("#key-field").hidden = local;
    document.querySelector("#clear-key-field").hidden = local;
    document.querySelector("#url-hint").textContent = local
      ? "仅支持本机 Ollama，默认 http://127.0.0.1:11434；请先启动 Ollama。"
      : "填写兼容接口的基础 URL，通常以 /v1 结尾。只支持 HTTPS 默认端口。";
  }
  function fill(config) {
    ["provider", "base_url", "model", "timeout", "max_tokens", "source_repo"].forEach((name) => { field(name).value = config[name]; });
    field("api_key").value = "";
    field("api_key").placeholder = config.api_key_set ? "已配置；同一接口留空保留" : "未配置；更换接口需重填密钥";
    field("clear_api_key").checked = false;
    providerHint();
    const overridden = config.environment_fields || [];
    if (overridden.length) say("配置已读取。部分选项由环境变量控制，页面保存不会覆盖环境变量。环境变量提供密钥时，更换接口需同时修改环境变量。");
  }
  function payload() {
    return {provider: field("provider").value, base_url: field("base_url").value.trim(),
      api_key: field("api_key").value, model: field("model").value.trim(),
      timeout: Number(field("timeout").value), max_tokens: Number(field("max_tokens").value),
      source_repo: field("source_repo").value.trim(), clear_api_key: field("clear_api_key").checked};
  }
  async function perform(action) {
    if (busy) return;
    setBusy(true);
    try { await action(); } catch (error) { say(error.message, true); }
    finally { setBusy(false); }
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    perform(async () => {
      const result = await request("/api/config", payload());
      fill(result);
      say("设置已保存。密钥只保存在本机用户配置目录，界面不会回显。");
    });
  });
  field("provider").addEventListener("change", () => {
    field("base_url").value = field("provider").value === "ollama" ? "http://127.0.0.1:11434" : "https://api.openai.com/v1";
    providerHint();
  });
  document.querySelector("#test-connection").addEventListener("click", () => perform(async () => {
    if (!form.reportValidity()) return;
    say("正在测试连接与 JSON 输出能力……");
    const result = await request("/api/test-connection", payload());
    say(result.message + " 当前测试不会保存设置。");
  }));
  async function runJob(kind) {
    const result = await request("/api/" + kind, {});
    say(result.message);
    let attempts = 0;
    while (attempts++ < 240) {
      await new Promise((resolve) => setTimeout(resolve, 2500));
      const current = await request("/api/status");
      if (!current.job.running) {
        say(current.job.message, !current.job.ok);
        return;
      }
    }
    say("任务仍在运行，可返回杂志查看状态。请勿重复启动。");
  }
  document.querySelector("#sync-content").addEventListener("click", () => perform(() => runJob("sync")));
  document.querySelector("#update-content").addEventListener("click", () => perform(() => runJob("update")));
  perform(async () => {
    token = (await request("/api/session")).token;
    fill(await request("/api/config"));
    say("本地服务已连接。可以修改设置或测试连接。");
  });
  window.addEventListener("pagehide", () => { field("api_key").value = ""; token = ""; });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      setBusy(false);
      perform(async () => {
        token = (await request("/api/session")).token;
        say("本地会话已恢复，未保留未保存的密钥。");
      });
    }
  });
})();
