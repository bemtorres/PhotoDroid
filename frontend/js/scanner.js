document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-scan")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) {
      UI.log("[ui] bridge no listo");
      return;
    }
    UI.log("[ui] iniciando escaneo…");
    UI.setProgress(5);
    bridge.startScan((raw) => {
      try {
        const data = JSON.parse(raw);
        UI.log(`[scan] status=${data.status}`);
      } catch (e) {
        UI.log(`[scan] error: ${e}`);
      }
      UI.setProgress(100);
    });
  });
});
