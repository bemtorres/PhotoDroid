(function () {
  "use strict";

  var root = document.querySelector("[data-scan-demo]");
  if (!root) return;

  var bar = root.querySelector("[data-demo-bar]");
  var stage = root.querySelector("[data-demo-stage]");
  var log = root.querySelector("[data-demo-log]");
  var findings = root.querySelector("[data-demo-findings]");
  var scoreEl = root.querySelector("[data-demo-score]");
  var alerts = root.querySelector("[data-demo-alerts]");
  var status = root.querySelector("[data-demo-status]");
  var startBtn = root.querySelector("[data-demo-start]");
  var resetBtn = root.querySelector("[data-demo-reset]");
  var device = root.querySelector("[data-demo-device]");

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var running = false;
  var timers = [];

  function t(key, fallback) {
    if (typeof siteT === "function") {
      var v = siteT(key);
      if (v && v !== key) return v;
    }
    return fallback || key;
  }

  function clearTimers() {
    timers.forEach(function (id) {
      clearTimeout(id);
    });
    timers = [];
  }

  function later(fn, ms) {
    timers.push(window.setTimeout(fn, ms));
  }

  function setProgress(pct) {
    if (bar) bar.style.width = Math.max(0, Math.min(100, pct)) + "%";
  }

  function setStatusKey(key) {
    if (!status) return;
    status.setAttribute("data-i18n", key);
    status.textContent = t(key, key);
  }

  function appendLog(key, cls) {
    if (!log) return;
    var li = document.createElement("li");
    li.className = "scan__line" + (cls ? " is-" + cls : "");
    li.textContent = t(key, key);
    log.appendChild(li);
    log.scrollTop = log.scrollHeight;
  }

  function resetDemo() {
    clearTimers();
    running = false;
    if (log) log.innerHTML = "";
    if (findings) findings.hidden = true;
    if (alerts) alerts.innerHTML = "";
    if (startBtn) startBtn.hidden = false;
    if (resetBtn) resetBtn.hidden = true;
    if (stage) {
      stage.setAttribute("data-i18n", "demo.stageIdle");
      stage.textContent = t("demo.stageIdle", "Pulsa «Iniciar escaneo»…");
    }
    if (device) {
      device.setAttribute("data-i18n", "demo.device");
      device.textContent = t("demo.device", "Pixel 7 · Android 14 · USB");
    }
    setProgress(0);
    setStatusKey("demo.statusIdle");
  }

  function addAlerts() {
    if (!alerts) return;
    var items = [
      { level: "high", key: "demo.a1" },
      { level: "high", key: "demo.a2" },
      { level: "mid", key: "demo.a3" },
      { level: "ok", key: "demo.a4" },
    ];
    alerts.innerHTML = "";
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.className = "scan__alert is-" + item.level;
      var badge = document.createElement("span");
      badge.className = "scan__alert-badge";
      badge.setAttribute("data-i18n", "demo.level." + item.level);
      badge.textContent = t("demo.level." + item.level, item.level);
      var text = document.createElement("span");
      text.setAttribute("data-i18n", item.key);
      text.textContent = t(item.key, item.key);
      li.appendChild(badge);
      li.appendChild(text);
      alerts.appendChild(li);
    });
  }

  function startDemo() {
    if (running) return;
    running = true;
    if (log) log.innerHTML = "";
    if (findings) findings.hidden = true;
    if (startBtn) startBtn.hidden = true;
    if (resetBtn) resetBtn.hidden = true;
    setProgress(0);
    setStatusKey("demo.statusScan");

    var script = [
      { at: 0, pct: 4, stage: "demo.stage1", log: "demo.l1" },
      { at: 450, pct: 18, stage: "demo.stage1", log: "demo.l2" },
      { at: 900, pct: 36, stage: "demo.stage2", log: "demo.l3" },
      { at: 1400, pct: 52, stage: "demo.stage2", log: "demo.l4" },
      { at: 1900, pct: 68, stage: "demo.stage3", log: "demo.l5" },
      { at: 2400, pct: 82, stage: "demo.stage3", log: "demo.l6" },
      { at: 2900, pct: 94, stage: "demo.stage4", log: "demo.l7" },
      { at: 3400, pct: 100, stage: "demo.stage5", log: "demo.l8" },
    ];

    script.forEach(function (step) {
      later(function () {
        setProgress(step.pct);
        if (stage) {
          stage.setAttribute("data-i18n", step.stage);
          stage.textContent = t(step.stage, step.stage);
        }
        if (step.log) appendLog(step.log);
      }, reduceMotion ? Math.min(step.at, 200) : step.at);
    });

    later(function () {
      running = false;
      setStatusKey("demo.statusDone");
      if (scoreEl) {
        scoreEl.setAttribute("data-i18n", "demo.scoreValue");
        scoreEl.textContent = t("demo.scoreValue", "3");
      }
      if (findings) findings.hidden = false;
      addAlerts();
      if (resetBtn) resetBtn.hidden = false;
      if (startBtn) startBtn.hidden = true;
    }, reduceMotion ? 400 : 3800);
  }

  if (startBtn) {
    startBtn.addEventListener("click", function () {
      startDemo();
    });
  }
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      resetDemo();
    });
  }

  document.addEventListener("site:lang", function () {
    if (!running) {
      var idle = stage && stage.getAttribute("data-i18n") === "demo.stageIdle";
      if (idle) {
        stage.textContent = t("demo.stageIdle", stage.textContent);
      }
      if (status && status.getAttribute("data-i18n")) {
        status.textContent = t(status.getAttribute("data-i18n"), status.textContent);
      }
      if (device) device.textContent = t("demo.device", device.textContent);
      if (log && !log.children.length === false) {
        // re-translate finished log lines is optional; leave as-is while running
      }
      if (findings && !findings.hidden) addAlerts();
    }
  });

  setProgress(0);
})();
