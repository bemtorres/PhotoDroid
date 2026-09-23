function renderReportsList(reports) {
  const tbody = document.getElementById("reports-table");
  const empty = document.getElementById("reports-empty");
  if (!tbody) return;
  const rows = reports || [];
  if (!rows.length) {
    tbody.innerHTML = "";
    if (empty) empty.classList.remove("hidden");
    return;
  }
  if (empty) empty.classList.add("hidden");
  tbody.innerHTML = rows
    .map((r) => {
      const sizeKb = Math.max(1, Math.round((r.size || 0) / 1024));
      return `
      <tr>
        <td class="cell-mono">${escapeHtml(r.filename)}</td>
        <td class="cell-mono" style="color: var(--color-muted)">${sizeKb} KB</td>
      </tr>`;
    })
    .join("");
}

function refreshReportsList() {
  if (!bridgeReady || !bridge) return;
  bridge.listReports((raw) => {
    try {
      const data = JSON.parse(raw);
      renderReportsList(data.reports || []);
    } catch (e) {
      UI.log(`[report] list error: ${e}`);
    }
  });
}

function bindReportSignals() {
  if (!bridgeReady || !bridge || bridge._reportSignalsBound) return;
  bridge._reportSignalsBound = true;

  bridge.reportReady.connect((info) => {
    UI.log(`[report] UI ← ${info?.filename}`);
    UI.setProgress(100);
    UI.setState("idle");
    refreshReportsList();
  });

  bridge.reportError.connect((reason) => {
    UI.log(`[report] UI error: ${reason}`);
    UI.setProgress(100);
    UI.setState("idle");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-export").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!bridgeReady || !bridge) {
        UI.log("[ui] bridge no listo");
        return;
      }
      const fmt = btn.dataset.format || "html";
      UI.log(`[ui] exportando reporte ${fmt}…`);
      bridge.exportReport(fmt, (raw) => UI.log(`[report] ${raw}`));
    });
  });
});
