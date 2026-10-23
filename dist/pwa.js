"use strict";
(() => {
  // 在开始异步工作前保存脚本 URL，兼容 GitHub Pages 的仓库子目录。
  const base = new URL(".", document.currentScript.src);
  const url = (path) => new URL(path, base).href;
  const loopback = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
  async function start() {
    if (document.querySelector(".gh-app-bar")) return;
    let local = loopback;
    try {
      const response = await fetch(url("site-config.json"), {cache: "no-store", credentials: "omit"});
      if (response.ok) local = loopback && (await response.json()).mode === "local";
    } catch {}
    const bar = document.createElement("aside");
    bar.className = "gh-app-bar";
    bar.setAttribute("aria-label", "应用操作");
    bar.dataset.mode = local ? "local" : "hosted";
    bar.innerHTML = '<span class="gh-app-state" role="status" aria-live="polite">正在检查离线缓存……</span><button type="button" data-action="install">安装应用</button><button type="button" data-action="fullscreen">全屏阅读</button>' + (local
      ? '<button type="button" data-action="sync">立即同步</button><a data-action="settings">设置</a>'
      : '<button type="button" data-action="refresh">检查更新</button>');
    if (local) bar.querySelector('[data-action="settings"]').href = url("settings.html");
    document.body.append(bar);
    document.body.classList.add("gh-pwa");
    const reserveSpace = () => document.documentElement.style.setProperty("--gh-app-reserved", Math.ceil(bar.getBoundingClientRect().height + 32) + "px");
    if ("ResizeObserver" in window) new ResizeObserver(reserveSpace).observe(bar);
    else window.addEventListener("resize", reserveSpace);
    reserveSpace();
    const state = bar.querySelector(".gh-app-state");
    let prompt = null;
    let worker = null;
    let ready = false;
    let revision = "";
    let generatedAt = "";
    let syncing = false;
    let updateRequested = false;
    const installed = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
    if (installed()) bar.querySelector('[data-action="install"]').hidden = true;
    function text(message) { state.textContent = message; }
    function offlineStatus() {
      return "已可离线阅读" + (generatedAt ? " · 内容更新于 " + generatedAt.slice(0, 16).replace("T", " ") : "");
    }
    function tellWorker(type) {
      const active = navigator.serviceWorker?.controller || worker?.active;
      if (active) active.postMessage({type});
    }
    function installGuide() {
      const message = "在 Chrome 或 Edge 的菜单中选择“安装页面为应用”，安装后从系统应用入口打开，即可使用没有地址栏和书签栏的独立窗口。手机可在浏览器菜单中选择“添加到主屏幕”。首次使用请等待“已可离线阅读”。";
      if (!("HTMLDialogElement" in window) || !HTMLDialogElement.prototype.showModal) {
        text(message);
        return;
      }
      const dialog = document.createElement("dialog");
      dialog.className = "gh-app-dialog";
      dialog.innerHTML = '<h2>安装为应用</h2><p></p><p>' + (local ? "本地服务停止后，可继续阅读已缓存内容。更新和设置需重新启动本地服务。" : "在线阅读无需 API Key。联网时检查最新内容，断网后可继续阅读已缓存的这一版。") + '</p><button type="button">知道了</button>';
      dialog.querySelector("p").textContent = message;
      dialog.querySelector("button").addEventListener("click", () => dialog.close());
      dialog.addEventListener("close", () => dialog.remove());
      document.body.append(dialog);
      dialog.showModal();
    }
    window.addEventListener("beforeinstallprompt", (event) => { event.preventDefault(); prompt = event; });
    window.addEventListener("appinstalled", () => { prompt = null; bar.querySelector('[data-action="install"]').hidden = true; text("应用已安装，可从系统应用入口启动。"); });
    async function serviceStatus() {
      if (!local) return null;
      try {
        const response = await fetch(url("api/status"), {cache: "no-store"});
        if (!response.ok) throw new Error();
        const status = await response.json();
        if (status.job.running) { text("正在执行" + (status.job.kind === "sync" ? "同步" : "采编") + "，可以继续阅读。"); return status; }
        if (ready) text(offlineStatus());
        return status;
      } catch {
        text(ready ? "离线阅读 · 设置与同步需先启动本地服务" : "本地服务未连接，离线缓存尚未确认。");
        return null;
      }
    }
    bar.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      if (button.dataset.action === "install") {
        if (prompt) { const pending = prompt; prompt = null; await pending.prompt(); await pending.userChoice; }
        else installGuide();
      } else if (button.dataset.action === "fullscreen") {
        try {
          if (document.fullscreenElement) await document.exitFullscreen();
          else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
          else text("此设备请使用系统窗口的全屏按钮。");
        } catch { text("请使用系统窗口的全屏按钮。"); }
      } else if (button.dataset.action === "refresh") {
        if (!worker && !navigator.serviceWorker?.controller) { window.location.reload(); return; }
        updateRequested = true;
        text("正在检查最新内容，可以继续阅读……");
        worker?.update().catch(() => {});
        tellWorker("PREPARE_CACHE");
      } else if (local && button.dataset.action === "sync" && !syncing) {
        syncing = true; button.disabled = true;
        try {
          const sessionResponse = await fetch(url("api/session"), {cache: "no-store"});
          if (!sessionResponse.ok) throw new Error();
          const session = await sessionResponse.json();
          const response = await fetch(url("api/sync"), {method: "POST", cache: "no-store", headers: {"Content-Type": "application/json", "X-GH-Daily-Token": session.token}, body: "{}"});
          const result = await response.json();
          if (!response.ok) { text(result.error || "同步暂未完成。"); return; }
          text("同步已开始，可以继续阅读。");
          for (let count = 0; count < 240; count++) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            const status = await serviceStatus();
            if (!status || !status.job.running) {
              if (status?.job.ok) { text(status.job.message); tellWorker("PREPARE_CACHE"); }
              else if (status) text(status.job.message);
              break;
            }
          }
        } catch { text("同步需先启动本地服务。已缓存内容可继续阅读。"); }
        finally { syncing = false; button.disabled = false; }
      }
    });
    document.addEventListener("fullscreenchange", () => {
      bar.querySelector('[data-action="fullscreen"]').textContent = document.fullscreenElement ? "退出全屏" : "全屏阅读";
    });
    if ("serviceWorker" in navigator && location.protocol !== "file:") {
      navigator.serviceWorker.addEventListener("message", (event) => {
        // 同域的其他项目也能广播消息；只信任本应用注册的 Worker。
        if (event.source?.scriptURL !== url("sw.js")) return;
        const data = event.data || {};
        if (data.type === "CACHE_READY") {
          const previous = revision;
          ready = true; revision = data.revision || ""; generatedAt = data.generated_at || "";
          text(previous && previous !== revision ? "新内容已缓存，刷新页面即可阅读。" : (updateRequested ? "当前已是最新缓存 · " : "") + offlineStatus());
          updateRequested = false;
        } else if (data.type === "CACHE_PROGRESS") text("正在缓存离线内容 " + data.completed + "/" + data.total + "……");
        else if (data.type === "CACHE_ERROR") {
          updateRequested = false;
          text(ready ? "本次缓存更新未完成，上一版仍可离线阅读。" : (local ? "离线缓存未完成，请保持本地服务运行后刷新重试。" : "离线缓存未完成，请联网后检查更新。当前仍可在线阅读。"));
        }
      });
      // 冷启动离线时注册更新可能失败，但已有控制器仍能确认完整缓存。
      tellWorker("CACHE_STATUS");
      navigator.serviceWorker.register(url("sw.js"), {scope: base.href, updateViaCache: "none"}).then(async (registration) => {
        worker = registration;
        await navigator.serviceWorker.ready;
        tellWorker("CACHE_STATUS");
        tellWorker("PREPARE_CACHE");
        setInterval(() => { registration.update().catch(() => {}); tellWorker("PREPARE_CACHE"); }, 15 * 60 * 1000);
      }).catch(() => text(ready ? offlineStatus() : (local ? "离线缓存暂不可用；请通过本地服务打开应用。" : "离线缓存暂不可用，可以继续在线阅读。")));
      navigator.serviceWorker.addEventListener("controllerchange", () => { tellWorker("CACHE_STATUS"); });
      window.addEventListener("online", () => { tellWorker("PREPARE_CACHE"); });
    } else text(location.protocol === "file:" ? "当前为离线文件；安装应用请先通过在线网址或本地服务打开。" : "此浏览器暂不支持离线安装，可以继续在线阅读。");
    if (local) { serviceStatus(); setInterval(serviceStatus, 30000); }
  }
  start();
})();
