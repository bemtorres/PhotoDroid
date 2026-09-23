const DEVICE_REASONS = {
  no_devices: "No devices found — connect USB and enable debugging",
  unauthorized: "Device unauthorized — accept the USB debugging prompt",
  offline: "Device offline — reconnect USB",
  no_permissions: "No ADB permissions (udev rules?)",
  no_online_device: "Devices listed but none online",
};

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
          UI.log(`[ui] detección omitida: ${data.reason || "unknown"}`);
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
    UI.setDevice(null, DEVICE_REASONS[reason] || reason);
    UI.setProgress(100);
    UI.log(`[device] ${DEVICE_REASONS[reason] || reason}`);
  });
}
