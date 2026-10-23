"use strict";
(() => {
  const form = document.querySelector("#settings-form");
  const status = document.querySelector("#status");
  let token = "";
  let busy = false;
  const field = (name) => form.elements.namedItem(name);
  const reconnect = "本地服务未连接。请重新打开桌面应用，或运行项目中的启动脚本，再刷新设置页。已缓存的杂志仍可阅读。";
  class LocalError extends Error {
    constructor(message, session = false) { super(message); this.session = session; }
  }
  function say(message, error = false) {
    status.textContent = message;
    status.dataset.error = String(error);
  }
  function setBusy(value) {
    busy = value;
    document.querySelectorAll("button").forEach((button) => { button.disabled = value; });
  }
  async function send(path, payload) {
    const controller = new AbortController();
    const seconds = Math.max(3, Math.min(120, Number(payload?.timeout) || 30));
    const timeout = path === "/api/test-connection" ? seconds * 4000 + 5000 : 10000;
    const timer = setTimeout(() => controller.abort(), timeout);
    const options = {cache: "no-store", credentials: "same-origin", signal: controller.signal};
    if (payload !== undefined) {
      options.method = "POST";
      options.headers = {"Content-Type": "application/json", "X-GH-Daily-Token": token};
      options.body = JSON.stringify(payload);
    }
    try {
      const response = await fetch(path, options);
      if (response.status === 401 || response.status === 403) throw new LocalError("本地会话已失效，请刷新设置页后重试。", true);
      if (!response.headers.get("Content-Type")?.includes("application/json")) throw new LocalError("本地服务返回了无法识别的内容，请重新启动服务并刷新设置页。");
      let result;
      try { result = await response.json(); }
      catch { throw new LocalError("本地服务返回了无法识别的内容，请重新启动服务并刷新设置页。"); }
      if (!result || typeof result !== "object" || Array.isArray(result)) throw new LocalError("本地服务返回了无法识别的内容，请重新启动服务并刷新设置页。");
      if (!response.ok) {
        if (response.status === 409) throw new LocalError("已有任务正在运行，请等待完成后再操作。");
        if (response.status === 400) throw new LocalError("本地操作未通过检查，请核对接口地址、模型、密钥和填写范围；测试失败时也请确认模型服务可用。");
        throw new LocalError("本地操作暂未完成，请重新启动服务后重试，或运行项目的诊断命令。");
      }
      return result;
    } catch (error) {
      if (error instanceof LocalError) throw error;
      throw new LocalError(payload === undefined ? reconnect : "本地服务连接中断或等待超时。请先确认服务和任务状态；操作可能已开始，请勿立即重复测试或采编。");
    } finally { clearTimeout(timer); }
  }
  async function refreshSession() {
    token = "";
    const session = await send("/api/session");
    if (typeof session.token !== "string" || !session.token) throw new LocalError("无法建立本地会话，请重新启动服务并刷新设置页。");
    token = session.token;
  }
  async function request(path, payload) {
    if (payload !== undefined && !token) await refreshSession();
    try { return await send(path, payload); }
    catch (error) {
      if (!error.session) throw error;
      token = "";
      try { await refreshSession(); }
      catch { throw new LocalError("本地会话已失效。请重新启动服务并刷新设置页，再手动重试。"); }
      // 更新凭据后仍由用户决定是否重试，避免连接测试或采编被重复执行。
      throw new LocalError("本地会话已更新，请再次点击所需操作。本次没有自动重试测试、保存或采编。");
    }
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
    if (!["cloud", "ollama"].includes(config.provider)
      || !["base_url", "model", "source_repo"].every((name) => typeof config[name] === "string")
      || !["timeout", "max_tokens"].every((name) => Number.isFinite(config[name]))
      || typeof config.api_key_set !== "boolean") throw new LocalError("本地配置响应不完整，请重新启动服务并刷新设置页。");
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
    try { await action(); } catch (error) { say(error instanceof LocalError ? error.message : "本地响应不完整，请重新启动服务并刷新设置页。", true); }
    finally { setBusy(false); }
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    perform(async () => {
      const result = await request("/api/config", payload());
      fill(result);
      say("设置已保存，不会自动采编或开启定时。密钥只保存在本机用户配置目录，界面不会回显。");
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
    if (result.ok !== true || typeof result.message !== "string") throw new LocalError("连接测试未返回有效结果，请检查模型服务后手动重试。");
    say(result.message + " 当前测试不会保存设置。");
  }));
  async function runJob(kind) {
    const result = await request("/api/" + kind, {});
    if (typeof result.message !== "string") throw new LocalError("未能确认任务是否启动，请先查看状态，不要重复执行。");
    say(result.message);
    let attempts = 0;
    while (attempts++ < 240) {
      await new Promise((resolve) => setTimeout(resolve, 2500));
      const current = await request("/api/status");
      if (typeof current.job?.running !== "boolean") throw new LocalError("任务状态暂不可用，请稍后返回杂志查看，避免重复执行。");
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
    await refreshSession();
    fill(await request("/api/config"));
    say("本地服务已连接。可以修改设置或测试连接。");
  });
  window.addEventListener("pagehide", () => { field("api_key").value = ""; token = ""; });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      setBusy(false);
      perform(async () => {
        await refreshSession();
        say("本地会话已恢复，未保留未保存的密钥。");
      });
    }
  });
})();
