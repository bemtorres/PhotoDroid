document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      UI.log(`[nav] ${btn.dataset.view}`);
    });
  });

  document.getElementById("btn-detect")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) {
      UI.log("[ui] bridge no listo");
      return;
    }
    UI.log("[ui] detectando dispositivo…");
    UI.setProgress(30);
    bridge.detectDevice((raw) => {
      try {
        const data = JSON.parse(raw);
        if (data.connected) {
          UI.setConnection(true);
          UI.setDevice(data.model, `${data.android} · ${data.serial}`);
        } else {
          UI.setConnection(false);
          UI.setDevice(null, data.reason || "not_implemented");
        }
      } catch (e) {
        UI.log(`[ui] detectDevice error: ${e}`);
      }
      UI.setProgress(100);
    });
  });
});
