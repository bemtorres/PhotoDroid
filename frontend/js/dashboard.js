const DEVICE_REASON_KEYS = {
  no_devices: "device.err.noDevices",
  unauthorized: "device.err.unauthorized",
  offline: "device.err.offline",
  no_permissions: "device.err.permissions",
  no_online_device: "device.err.notOnline",
  adb_not_found: "device.err.adbNotFound",
  already_running: "device.err.alreadyRunning",
};

function deviceErrorText(reason) {
  const key = DEVICE_REASON_KEYS[reason];
  if (key) return t(key);
  if (typeof reason === "string" && reason.startsWith("unexpected:")) {
    return `${t("device.err.failed")}: ${reason.replace("unexpected:", "").trim()}`;
  }
  return reason || t("device.err.failed");
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      UI.showView(view);
      UI.log(`[nav] ${view}`);
      if (view === "scanner" && bridgeReady && bridge) {
        bridge.listApps();
      }
    });
  });

  document.getElementById("btn-detect")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) {
      UI.log("[ui] bridge no listo");
      return;
    }
    UI.log("[ui] detectando dispositivo…");
    UI.setProgress(15);
    bridge.detectDevice((raw) => {
      try {
        const data = JSON.parse(raw);
        if (!data.started) {
          const text = deviceErrorText(data.reason || "unknown");
          UI.log(`[ui] ${text}`);
          if (data.reason === "already_running") {
            UI.setDevice(null, text);
            UI.setState("idle");
          }
          UI.setProgress(100);
        }
      } catch (e) {
        UI.log(`[ui] detectDevice error: ${e}`);
      }
    });
  });
});

function bindDeviceSignals() {
  if (!bridgeReady || !bridge || bridge._deviceSignalsBound) return;
  bridge._deviceSignalsBound = true;

  bridge.deviceFound.connect((info) => {
    UI.setConnection(true);
    UI.setDevice(
      info.model || info.serial,
      `Android ${info.android || "?"} · ${info.serial || "?"}`
    );
    UI.setProgress(100);
    UI.log(
      `[device] conectado: ${info.model || info.serial} (SDK ${info.sdk || "?"}, ${info.brand || "?"})`
    );
    if (info.battery != null) {
      UI.log(`[device] batería ${info.battery}%`);
    }
  });

  bridge.deviceError.connect((reason) => {
    UI.setConnection(false);
    const text = deviceErrorText(reason);
    UI.setDevice(null, text);
    UI.setProgress(100);
    UI.setState("idle");
    UI.log(`[device] ${text} (${reason})`);
  });
}
