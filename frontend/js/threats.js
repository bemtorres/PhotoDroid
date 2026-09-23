function levelBadge(level) {
  const map = {
    critical: "chip-danger",
    high: "chip-danger",
    suspicious: "chip-warning",
    low: "chip-success",
  };
  const cls = map[level] || "chip-neutral";
  const label = t(`risk.${level || "unknown"}`);
  return `<span class="chip ${cls}">${escapeHtml(label)}</span>`;
}

function renderThreats(report) {
  if (!report) return;

  UI.setRisk(report.risk_level, report.risk_score ?? 0);
  UI.setStat("threat-count", report.threat_count ?? 0);
  UI.setStat("threat-findings-count", report.findings?.length ?? 0);

  const servicesEl = document.getElementById("threat-services");
  if (servicesEl) {
    const a11y = report.services?.accessibility_services || [];
    const overlay = report.services?.overlay_apps || [];
    servicesEl.textContent = `A11y: ${a11y.length} · Overlay: ${overlay.length}`;
  }

  const tbody = document.getElementById("threats-table");
  const empty = document.getElementById("threats-empty");
  const findings = report.findings || [];

  if (!tbody) return;

  if (!findings.length) {
    tbody.innerHTML = "";
    if (empty) empty.classList.remove("hidden");
    return;
  }

  if (empty) empty.classList.add("hidden");
  tbody.innerHTML = findings
    .map((f) => {
      const reasons = (f.reasons || [])
        .map((r) => `${r.detail || r.code} (+${r.weight})`)
        .join(" · ");
      const scoreClass = f.score >= 75 ? "score-high" : f.score >= 50 ? "score-mid" : "score-ok";
      const pkg = escapeHtml(f.package);
      const system = f.system ? "1" : "0";
      const disable = f.system
        ? ""
        : `<button type="button" class="btn btn-secondary q-action" data-action="disable" data-package="${pkg}" data-system="${system}">${escapeHtml(t("quarantine.disable"))}</button>`;
      const uninstall = f.system
        ? ""
        : `<button type="button" class="btn btn-danger q-action" data-action="uninstall" data-package="${pkg}" data-system="${system}">${escapeHtml(t("quarantine.uninstall"))}</button>`;
      return `
      <tr>
        <td class="cell-mono">${pkg}</td>
        <td class="cell-strong ${scoreClass}">${f.score}</td>
        <td>${levelBadge(f.level)}</td>
        <td>${escapeHtml(reasons || "—")}</td>
        <td>
          <div class="row-actions">
            <button type="button" class="btn btn-secondary q-action" data-action="force_stop" data-package="${pkg}" data-system="${system}">${escapeHtml(t("quarantine.forceStop"))}</button>
            ${disable}
            ${uninstall}
          </div>
        </td>
      </tr>`;
    })
    .join("");

  tbody.querySelectorAll(".q-action").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const package = btn.dataset.package;
      const system = btn.dataset.system === "1";
      if (typeof requestQuarantine === "function") {
        requestQuarantine(action, package, system);
      }
    });
  });
}

function bindThreatSignals() {
  if (!bridgeReady || !bridge || bridge._threatSignalsBound) return;
  bridge._threatSignalsBound = true;

  bridge.threatsReady.connect((report) => {
    renderThreats(report || {});
    UI.log(
      `[threat] UI ← score=${report?.risk_score ?? "?"} level=${report?.risk_level ?? "?"} findings=${report?.findings?.length ?? 0}`
    );
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-reeval")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) {
      UI.log("[ui] bridge no listo");
      return;
    }
    UI.log("[ui] re-evaluando amenazas…");
    bridge.reevaluateThreats((raw) => UI.log(`[threat] ${raw}`));
  });
});
