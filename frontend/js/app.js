let bridge = null;
let bridgeReady = false;

const UI = {
  log(msg) {
    const time = new Date().toLocaleTimeString();
    const line = `[${time}] ${msg}`;
    document.querySelectorAll("#log-console, #log-console-scanner").forEach((box) => {
      const row = document.createElement("div");
      row.textContent = line;
      box.appendChild(row);
      box.scrollTop = box.scrollHeight;
    });
  },
  setProgress(value) {
    const v = Math.max(0, Math.min(100, Number(value) || 0));
    document.querySelectorAll(".progress-fill").forEach((bar) => {
      bar.style.width = `${v}%`;
    });
    document.querySelectorAll("#progress-label").forEach((label) => {
      label.textContent = `${v}%`;
    });
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
  setStat(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value);
  },
  showView(name) {
    document.querySelectorAll(".view-panel").forEach((panel) => panel.classList.add("hidden"));
    const target = document.getElementById(`view-${name}`);
    if (target) target.classList.remove("hidden");

    const titles = {
      dashboard: "header.title",
      scanner: "scanner.title",
      apps: "nav.apps",
      reports: "nav.reports",
    };
    const titleEl = document.querySelector("header h1");
    if (titleEl && titles[name]) titleEl.textContent = t(titles[name]);

    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.view === name);
    });
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

    if (typeof bindDeviceSignals === "function") bindDeviceSignals();
    if (typeof bindScanSignals === "function") bindScanSignals();

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
    document.querySelectorAll("#log-console, #log-console-scanner").forEach((box) => {
      box.innerHTML = "";
    });
  });

  initBridge();
});
