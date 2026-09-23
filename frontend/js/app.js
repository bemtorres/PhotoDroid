let bridge = null;
let bridgeReady = false;

const UI = {
  log(msg) {
    const box = document.getElementById("log-console");
    if (!box) return;
    const line = document.createElement("div");
    const time = new Date().toLocaleTimeString();
    line.textContent = `[${time}] ${msg}`;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
  },
  setProgress(value) {
    const v = Math.max(0, Math.min(100, Number(value) || 0));
    const bar = document.getElementById("progress-bar");
    const label = document.getElementById("progress-label");
    if (bar) bar.style.width = `${v}%`;
    if (label) label.textContent = `${v}%`;
  },
  setConnection(connected) {
    const dot = document.getElementById("conn-dot");
    const label = document.getElementById("conn-label");
    if (!dot || !label) return;
    dot.className = connected
      ? "h-2 w-2 rounded-full bg-emerald-400 pulse-dot"
      : "h-2 w-2 rounded-full bg-slate-500";
    label.textContent = connected ? t("device.connected") : t("device.waiting");
  },
  setDevice(model, meta) {
    const modelEl = document.getElementById("device-model");
    const metaEl = document.getElementById("device-meta");
    if (modelEl) modelEl.textContent = model || "—";
    if (metaEl) metaEl.textContent = meta || "Android · USB";
  },
};

function initBridge() {
  if (typeof QWebChannel === "undefined") {
    UI.log("[ui] QWebChannel no disponible");
    return;
  }
  new QWebChannel(qt.webChannelTransport, (channel) => {
    bridge = channel.objects.bridge;
    bridgeReady = !!bridge;
    if (!bridge) {
      UI.log("[ui] bridge no registrado");
      return;
    }

    bridge.log.connect((msg) => UI.log(msg));
    bridge.progress.connect((value) => UI.setProgress(value));
    bridge.stateChanged.connect((state) => UI.log(`[state] ${state}`));
    bridge.languageChanged.connect((lang) => {
      applyI18n(lang);
      const sel = document.getElementById("lang-select");
      if (sel) sel.value = lang;
      UI.log(`[i18n] ${lang}`);
    });

    bridge.getAppInfo((raw) => {
      try {
        const info = JSON.parse(raw);
        applyI18n(info.language || "en");
        const sel = document.getElementById("lang-select");
        if (sel) sel.value = info.language || "en";
        UI.log(`[ui] ${info.name} v${info.version} · lang=${info.language}`);
      } catch (e) {
        UI.log(`[ui] getAppInfo error: ${e}`);
      }
    });

    UI.log("[ui] QWebChannel listo");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  applyI18n("en");

  const langSelect = document.getElementById("lang-select");
  if (langSelect) {
    langSelect.addEventListener("change", () => {
      applyI18n(langSelect.value);
      UI.log(`[i18n] ${langSelect.value}`);
    });
  }

  document.getElementById("btn-clear-log")?.addEventListener("click", () => {
    const box = document.getElementById("log-console");
    if (box) box.innerHTML = "";
  });

  initBridge();
});
