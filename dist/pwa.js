"use strict";
(() => {
  if (document.querySelector(".gh-app-bar")) return;
  const bar = document.createElement("aside");
  bar.className = "gh-app-bar";
  bar.setAttribute("aria-label", "应用操作");
  bar.innerHTML = '<span class="gh-app-state" role="status" aria-live="polite">正在检查离线缓存……</span><button type="button" data-action="install">安装应用</button><button type="button" data-action="fullscreen">全屏阅读</button><button type="button" data-action="sync">立即同步</button><a href="/settings.html">设置</a>';
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
  let syncing = false;
  const installed = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  if (installed()) bar.querySelector('[data-action="install"]').hidden = true;
  function text(message) { state.textContent = message; }
  function tellWorker(type) {
    const active = navigator.serviceWorker?.controller || worker?.active;
    if (active) active.postMessage({type});
  }
  function installGuide() {
    if (!("HTMLDialogElement" in window) || !HTMLDialogElement.prototype.showModal) {
      window.location.href = "/settings.html";
      return;
    }
    const dialog = document.createElement("dialog");
    dialog.className = "gh-app-dialog";
    dialog.innerHTML = '<h2>安装为桌面应用</h2><p>在 Chrome 或 Edge 的菜单中选择“安装页面为应用”，安装后从系统应用入口打开，即可使用没有地址栏和书签栏的独立窗口。</p><p>首次使用请等待“已可离线阅读”。本地服务停止后，可继续阅读已缓存内容。</p><button type="button">知道了</button>';
    dialog.querySelector("button").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => dialog.remove());
    document.body.append(dialog);
    dialog.showModal();
  }
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault(); prompt = event;
  });
  window.addEventListener("appinstalled", () => { prompt = null; bar.querySelector('[data-action="install"]').hidden = true; text("应用已安装，可从系统应用入口启动。"); });
  async function serviceStatus() {
    try {
      const response = await fetch("/api/status", {cache: "no-store"});
      if (!response.ok) throw new Error();
      const status = await response.json();
      if (status.job.running) { text("正在执行" + (status.job.kind === "sync" ? "同步" : "采编") + "，可以继续阅读。"); return status; }
      if (ready) text("已可离线阅读" + (revision ? " · " + revision.slice(0, 8) : "") + (status.generated_at && status.generated_at !== "暂未获取" ? " · 更新于 " + status.generated_at.slice(0, 16).replace("T", " ") : ""));
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
    } else if (button.dataset.action === "sync" && !syncing) {
      syncing = true; button.disabled = true;
      try {
        const sessionResponse = await fetch("/api/session", {cache: "no-store"});
        if (!sessionResponse.ok) throw new Error();
        const session = await sessionResponse.json();
        const response = await fetch("/api/sync", {method: "POST", cache: "no-store", headers: {"Content-Type": "application/json", "X-GH-Daily-Token": session.token}, body: "{}"});
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
      const data = event.data || {};
      if (data.type === "CACHE_READY") {
        const previous = revision;
        ready = true; revision = data.revision || "";
        text(previous && previous !== revision ? "新内容已缓存，刷新页面即可阅读。" : "已可离线阅读 · " + revision.slice(0, 8));
      } else if (data.type === "CACHE_PROGRESS") text("正在缓存离线内容 " + data.completed + "/" + data.total + "……");
      else if (data.type === "CACHE_ERROR") text(ready ? "本次缓存更新未完成，上一版仍可离线阅读。" : "离线缓存未完成，请保持本地服务运行后刷新重试。");
    });
    // 冷启动离线时注册更新可能失败，但已有控制器仍能确认完整缓存。
    tellWorker("CACHE_STATUS");
    navigator.serviceWorker.register("/sw.js", {scope: "/", updateViaCache: "none"}).then(async (registration) => {
      worker = registration;
      await navigator.serviceWorker.ready;
      tellWorker("CACHE_STATUS");
      tellWorker("PREPARE_CACHE");
      setInterval(() => { registration.update().catch(() => {}); tellWorker("PREPARE_CACHE"); }, 15 * 60 * 1000);
    }).catch(() => text(ready ? "离线阅读 · 设置与同步需先启动本地服务" : "离线缓存暂不可用；请通过本地服务打开应用。"));
    navigator.serviceWorker.addEventListener("controllerchange", () => { tellWorker("CACHE_STATUS"); });
  } else text(location.protocol === "file:" ? "当前为离线文件；安装应用请先启动本地服务。" : "此浏览器暂不支持离线安装。");
  serviceStatus();
  setInterval(serviceStatus, 30000);
})();
