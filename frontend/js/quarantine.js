let pendingQuarantine = null;

function openConfirmModal(message, onConfirm) {
  const modal = document.getElementById("confirm-modal");
  const msg = document.getElementById("modal-message");
  if (!modal || !msg) return;
  msg.textContent = message;
  modal.classList.remove("hidden");

  const cancelBtn = document.getElementById("modal-cancel");
  const confirmBtn = document.getElementById("modal-confirm");

  const cleanup = () => {
    modal.classList.add("hidden");
    pendingQuarantine = null;
    cancelBtn?.removeEventListener("click", onCancel);
    confirmBtn?.removeEventListener("click", onOk);
  };
  const onCancel = () => cleanup();
  const onOk = () => {
    cleanup();
    onConfirm();
  };

  cancelBtn?.addEventListener("click", onCancel);
  confirmBtn?.addEventListener("click", onOk);
}

function requestQuarantine(action, package, system) {
  if (!bridgeReady || !bridge) {
    UI.log("[ui] bridge no listo");
    return;
  }
  const label = t(`quarantine.action.${action}`);
  const message = t("quarantine.confirm").replace("{action}", label).replace("{package}", package);
  openConfirmModal(message, () => {
    UI.log(`[quarantine] confirmado ${action} · ${package}`);
    bridge.quarantineAction(action, package, true, (raw) => UI.log(`[quarantine] ${raw}`));
  });
}

function renderQuarantineLog(entries) {
  const tbody = document.getElementById("quarantine-log-table");
  const empty = document.getElementById("quarantine-log-empty");
  if (!tbody) return;
  const rows = entries || [];
  if (!rows.length) {
    tbody.innerHTML = "";
    if (empty) empty.classList.remove("hidden");
    return;
  }
  if (empty) empty.classList.add("hidden");
  tbody.innerHTML = rows
    .map((e) => {
      const time = String(e.timestamp || "").replace("T", " ").slice(0, 19);
      const ok = e.ok
        ? `<span class="chip chip-success">${escapeHtml(t("quarantine.ok"))}</span>`
        : `<span class="chip chip-danger">${escapeHtml(t("quarantine.fail"))}</span>`;
      return `
      <tr>
        <td class="cell-mono" style="color: var(--color-muted)">${escapeHtml(time)}</td>
        <td><span class="chip chip-accent">${escapeHtml(e.action || "—")}</span></td>
        <td class="cell-mono">${escapeHtml(e.package || "—")}</td>
        <td>${ok}</td>
      </tr>`;
    })
    .join("");
}

function refreshQuarantineLog() {
  if (!bridgeReady || !bridge) return;
  bridge.listQuarantineLog((raw) => {
    try {
      const data = JSON.parse(raw);
      renderQuarantineLog(data.entries || []);
    } catch (e) {
      UI.log(`[quarantine] log error: ${e}`);
    }
  });
}

function bindQuarantineSignals() {
  if (!bridgeReady || !bridge || bridge._quarantineSignalsBound) return;
  bridge._quarantineSignalsBound = true;

  bridge.quarantineReady.connect((entry) => {
    UI.log(
      `[quarantine] UI ← ${entry?.action} ${entry?.package} ok=${entry?.ok}`
    );
    refreshQuarantineLog();
  });

  bridge.quarantineError.connect((reason) => {
    UI.log(`[quarantine] UI error: ${reason}`);
  });

  bridge.quarantineLogReady.connect((entries) => {
    renderQuarantineLog(entries || []);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-quarantine-log")?.addEventListener("click", () => {
    UI.log("[ui] refrescando auditoría de cuarentena…");
    refreshQuarantineLog();
  });
});
