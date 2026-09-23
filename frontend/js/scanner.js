function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderApps(apps) {
  const tbody = document.getElementById("apps-table");
  if (!tbody) return;
  UI.setStat("stat-apps", apps.length);
  tbody.innerHTML = apps
    .map(
      (app) => `
    <tr>
      <td class="cell-mono">${escapeHtml(app.package)}</td>
      <td>
        <span class="chip ${app.system ? "chip-neutral" : "chip-accent"}">
          ${app.system ? "system" : "user"}
        </span>
      </td>
      <td class="cell-mono" style="color: var(--color-muted)">${escapeHtml(app.apk_path || "—")}</td>
    </tr>`
    )
    .join("");
}

function renderPermissions(results, services) {
  const tbody = document.getElementById("perms-table");
  if (tbody && results) {
    const sorted = [...results].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));
    tbody.innerHTML = sorted
      .map((row) => {
        const flags = [];
        if (row.overlay) flags.push("overlay");
        if (row.accessibility) flags.push("a11y");
        const score = row.risk_score || 0;
        const scoreClass = score >= 50 ? "score-high" : score >= 20 ? "score-mid" : "score-ok";
        return `
      <tr>
        <td class="cell-mono">${escapeHtml(row.package)}</td>
        <td>${escapeHtml((row.labels || row.dangerous || []).join(", ") || "—")}</td>
        <td>${escapeHtml(flags.join(" · ") || "—")}</td>
        <td class="cell-strong ${scoreClass}">${score}</td>
      </tr>`;
      })
      .join("");

    UI.setStat(
      "stat-risky",
      results.filter((r) => (r.risk_score || 0) > 0 || (r.dangerous || []).length).length
    );
  }

  updateServices(services);
}

function updateServices(services) {
  const summary = document.getElementById("services-summary");
  if (!summary || !services) return;
  const a11y = services.accessibility_services || [];
  const overlay = services.overlay_apps || [];
  summary.textContent = `Accessibility: ${a11y.join(", ") || "none"} · Overlay: ${overlay.join(", ") || "none"}`;
}

function renderProcesses(processes) {
  const tbody = document.getElementById("procs-table");
  if (!tbody) return;
  UI.setStat("stat-procs", processes.length);
  tbody.innerHTML = processes
    .map(
      (p) => `
    <tr>
      <td class="cell-mono" style="color: var(--color-muted)">${escapeHtml(p.pid)}</td>
      <td>${escapeHtml(p.user || "—")}</td>
      <td class="cell-mono">${escapeHtml(p.name)}</td>
    </tr>`
    )
    .join("");
}

function showScanTab(name) {
  document.querySelectorAll(".scan-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === name);
  });
  document.querySelectorAll(".scan-tab-panel").forEach((panel) => panel.classList.add("hidden"));
  const target = document.getElementById(`tab-${name}`);
  if (target) target.classList.remove("hidden");
}

function bindScanSignals() {
  if (!bridgeReady || !bridge || bridge._scanSignalsBound) return;
  bridge._scanSignalsBound = true;

  bridge.appsReady.connect((apps) => {
    renderApps(apps || []);
    UI.log(`[ui] tabla apps: ${(apps || []).length}`);
  });

  bridge.permissionsReady.connect((results) => {
    renderPermissions(results || [], null);
    UI.log(`[ui] tabla permisos: ${(results || []).length}`);
  });

  bridge.servicesReady.connect((services) => {
    updateServices(services || {});
  });

  bridge.processesReady.connect((processes) => {
    renderProcesses(processes || []);
    UI.log(`[ui] tabla procesos: ${(processes || []).length}`);
  });

  bridge.scanStage.connect((stage) => {
    UI.setStage(stage);
  });

  bridge.scanFinished.connect((summary) => {
    UI.setProgress(100);
    UI.setStage("done");
    if (summary) {
      UI.setStat("stat-apps", summary.apps || 0);
      UI.setStat("stat-risky", summary.apps_with_dangerous || 0);
      UI.setStat("stat-procs", summary.processes || 0);
      UI.setStat("threat-count", summary.threat_count ?? summary.apps_with_dangerous ?? 0);
      if (summary.risk_level) {
        UI.setRisk(summary.risk_level, summary.risk_score ?? 0);
      }
    }
    UI.log("[ui] escaneo completo finalizado");
  });

  bridge.scanError.connect((reason) => {
    UI.setProgress(100);
    UI.setState("idle");
    UI.log(`[ui] scan error: ${reason}`);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".scan-tab").forEach((tab) => {
    tab.addEventListener("click", () => showScanTab(tab.dataset.tab));
  });

  document.getElementById("btn-scan")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) {
      UI.log("[ui] bridge no listo");
      return;
    }
    UI.log("[ui] iniciando escaneo completo…");
    UI.showView("scanner");
    UI.setProgress(0);
    bridge.startScan((raw) => {
      try {
        const data = JSON.parse(raw);
        UI.log(`[scan] status=${data.started ? "started" : data.reason}`);
      } catch (e) {
        UI.log(`[scan] error: ${e}`);
      }
    });
  });

  document.getElementById("btn-load-apps")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) return;
    UI.log("[ui] cargando aplicaciones…");
    bridge.listApps((raw) => UI.log(`[apps] ${raw}`));
  });

  document.getElementById("btn-scan-perms")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) return;
    UI.log("[ui] analizando permisos…");
    showScanTab("perms");
    bridge.scanPermissions((raw) => UI.log(`[perms] ${raw}`));
  });

  document.getElementById("btn-load-procs")?.addEventListener("click", () => {
    if (!bridgeReady || !bridge) return;
    UI.log("[ui] cargando procesos…");
    showScanTab("procs");
    bridge.listProcesses((raw) => UI.log(`[procs] ${raw}`));
  });
});
