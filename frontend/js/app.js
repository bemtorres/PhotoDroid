let bridge = null;
let bridgeReady = false;

const BUSY_STATES = new Set([
  "detecting",
  "loading_apps",
  "scanning_permissions",
  "loading_processes",
  "scanning",
  "quarantining",
  "exporting",
]);

const UI = {
  log(msg) {
    const time = new Date().toLocaleTimeString();
    const line = `[${time}] ${msg}`;
    const isError = /error|fail|unexpected/i.test(msg);
    document.querySelectorAll("#log-console, #log-console-scanner").forEach((box) => {
      const row = document.createElement("div");
      row.textContent = line;
      if (isError) row.classList.add("log-error");
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
    dot.classList.toggle("is-online", !!connected);
    dot.classList.toggle("is-offline", !connected);
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
  setState(state) {
    const name = state || "idle";
    const badge = document.getElementById("state-badge");
    if (badge) {
      badge.textContent = name;
      badge.classList.toggle("is-busy", BUSY_STATES.has(name));
    }

    const busy = BUSY_STATES.has(name);
    document.querySelectorAll(".action-btn").forEach((btn) => {
      if (btn.id === "btn-cancel-scan") return;
      btn.disabled = busy;
    });

    const cancelBtn = document.getElementById("btn-cancel-scan");
    if (cancelBtn) {
      cancelBtn.classList.toggle("hidden", name !== "scanning");
      cancelBtn.disabled = name !== "scanning";
    }

    const stageKey = `stage.${name}`;
    const stageEl = document.getElementById("stage-label");
    if (stageEl) stageEl.textContent = t(stageKey);
  },
  setStage(stage) {
    const raw = stage || "idle";
    const el = document.getElementById("scan-stage");
    if (el) el.textContent = t(`stage.${raw}`) || raw;
    const stageEl = document.getElementById("stage-label");
    if (stageEl) stageEl.textContent = t(`stage.${raw}`);
  },
  setRisk(level, score) {
    const levelEl = document.getElementById("risk-level");
    const scoreEl = document.getElementById("risk-score");
    const threatLevel = document.getElementById("threat-risk-level");
    const threatScore = document.getElementById("threat-risk-score");

    const levelKey = `risk.${level || "unknown"}`;
    const text = t(levelKey);
    const cls =
      level === "critical" || level === "high"
        ? "risk-critical"
        : level === "suspicious"
          ? "risk-suspicious"
          : "risk-low";

    [levelEl, threatLevel].forEach((el) => {
      if (!el) return;
      el.textContent = text;
      el.classList.remove("risk-low", "risk-suspicious", "risk-high", "risk-critical");
      el.classList.add(cls);
      el.removeAttribute("data-i18n");
    });

    const scoreText = `${score ?? 0} / 100`;
    if (scoreEl) scoreEl.textContent = scoreText;
    if (threatScore) threatScore.textContent = scoreText;
  },
  showView(name) {
    document.querySelectorAll(".view-panel").forEach((panel) => panel.classList.add("hidden"));
    const target = document.getElementById(`view-${name}`);
    if (target) target.classList.remove("hidden");

    const titles = {
      dashboard: "header.title",
      scanner: "scanner.title",
      threats: "threats.title",
      apps: "nav.apps",
      reports: "nav.reports",
      settings: "nav.settings",
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
    bridge.stateChanged.connect((state) => {
      UI.setState(state);
      UI.log(`[state] ${state}`);
    });
    bridge.languageChanged.connect((lang) => {
      applyI18n(lang);
      const sel = document.getElementById("lang-select");
      if (sel) sel.value = lang;
      UI.log(`[i18n] ${lang}`);
    });

    if (typeof bindDeviceSignals === "function") bindDeviceSignals();
    if (typeof bindScanSignals === "function") bindScanSignals();
    if (typeof bindThreatSignals === "function") bindThreatSignals();
    if (typeof bindQuarantineSignals === "function") bindQuarantineSignals();
    if (typeof bindReportSignals === "function") bindReportSignals();
    if (typeof bindSettingsSignals === "function") bindSettingsSignals();

    if (typeof loadSettingsForm === "function") loadSettingsForm();
    if (typeof refreshReportsList === "function") refreshReportsList();
    if (typeof refreshQuarantineLog === "function") refreshQuarantineLog();

    bridge.getAppInfo((raw) => {
      try {
        const info = JSON.parse(raw);
        applyI18n(info.language || "en");
        const sel = document.getElementById("lang-select");
        if (sel) sel.value = info.language || "en";
        UI.log(`[ui] ${info.name} v${info.version} · lang=${info.language} · phase=${info.phase ?? "?"}`);
      } catch (e) {
        UI.log(`[ui] getAppInfo error: ${e}`);
      }
    });

    UI.setState("idle");
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

  document.getElementById("btn-cancel-scan")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) return;
    bridge.cancelScan((raw) => UI.log(`[scan] cancel → ${raw}`));
  });

  initBridge();
});
