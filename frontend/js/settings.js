function loadSettingsForm() {
  if (!bridgeReady || !bridge) return;
  bridge.getSettings((raw) => {
    try {
      const s = JSON.parse(raw);
      applySettingsToForm(s);
    } catch (e) {
      UI.log(`[settings] load error: ${e}`);
    }
  });
}

function applySettingsToForm(s) {
  const lang = document.getElementById("set-language");
  const adb = document.getElementById("set-adb");
  const thLow = document.getElementById("set-th-low");
  const thSusp = document.getElementById("set-th-susp");
  const thHigh = document.getElementById("set-th-high");
  const incSys = document.getElementById("set-inc-system");
  const permSys = document.getElementById("set-perm-system");
  const reportsDir = document.getElementById("set-reports-dir");

  if (lang && s.language) lang.value = s.language;
  if (adb) adb.value = s.adb_path || "adb";
  const th = s.risk_thresholds || {};
  if (thLow) thLow.value = th.low ?? 20;
  if (thSusp) thSusp.value = th.suspicious ?? 50;
  if (thHigh) thHigh.value = th.high ?? 75;
  const scan = s.scan || {};
  if (incSys) incSys.checked = scan.include_system_apps !== false;
  if (permSys) permSys.checked = !!scan.permission_scan_system;
  if (reportsDir) reportsDir.value = (s.reports || {}).output_dir || "reports";
}

function collectSettingsForm() {
  const thLow = Number(document.getElementById("set-th-low")?.value || 20);
  const thSusp = Number(document.getElementById("set-th-susp")?.value || 50);
  const thHigh = Number(document.getElementById("set-th-high")?.value || 75);
  return {
    language: document.getElementById("set-language")?.value || "en",
    adb_path: document.getElementById("set-adb")?.value || "adb",
    risk_thresholds: {
      low: thLow,
      suspicious: thSusp,
      high: thHigh,
    },
    scan: {
      include_system_apps: !!document.getElementById("set-inc-system")?.checked,
      permission_scan_system: !!document.getElementById("set-perm-system")?.checked,
    },
    reports: {
      output_dir: document.getElementById("set-reports-dir")?.value || "reports",
      default_format: "html",
    },
  };
}

function bindSettingsSignals() {
  if (!bridgeReady || !bridge || bridge._settingsSignalsBound) return;
  bridge._settingsSignalsBound = true;

  bridge.settingsSaved.connect((settings) => {
    const status = document.getElementById("settings-status");
    if (status) status.textContent = t("settings.saved");
    if (settings) applySettingsToForm(settings);
    UI.log("[settings] guardado");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-save-settings")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) {
      UI.log("[ui] bridge no listo");
      return;
    }
    const payload = collectSettingsForm();
    const status = document.getElementById("settings-status");
    if (status) status.textContent = "…";
    UI.log("[ui] guardando ajustes…");
    bridge.saveSettings(JSON.stringify(payload), (raw) => {
      try {
        const data = JSON.parse(raw);
        if (status) status.textContent = data.ok ? t("settings.saved") : data.error || "error";
        if (data.ok && data.settings) applySettingsToForm(data.settings);
        if (data.ok && data.settings?.language) {
          applyI18n(data.settings.language);
          const sel = document.getElementById("lang-select");
          if (sel) sel.value = data.settings.language;
        }
        UI.log(`[settings] ${raw}`);
      } catch (e) {
        UI.log(`[settings] error: ${e}`);
      }
    });
  });
});
