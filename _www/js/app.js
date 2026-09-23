(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ——— i18n (default es, before reveal/palette render) ——— */
  if (typeof applySiteI18n === "function") {
    applySiteI18n(typeof getStoredLang === "function" ? getStoredLang() : "es");
  }

  function bindLangSelects() {
    var selects = document.querySelectorAll("[data-site-lang]");
    selects.forEach(function (select) {
      select.addEventListener("change", function () {
        if (typeof setSiteLang === "function") setSiteLang(select.value);
      });
    });
  }

  bindLangSelects();

  /* Reveal once */
  var reveals = document.querySelectorAll(".reveal");
  if (reduceMotion) {
    reveals.forEach(function (el) {
      el.classList.add("is-in");
    });
  } else if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    reveals.forEach(function (el) {
      io.observe(el);
    });
  } else {
    reveals.forEach(function (el) {
      el.classList.add("is-in");
    });
  }

  /* Type-in once in hero terminal */
  var typed = document.querySelector("[data-type-in]");
  if (typed) {
    var full = typed.getAttribute("data-type-in") || "";
    var target = typed.querySelector("[data-type-target]");
    var caret = typed.querySelector(".caret");
    if (target) {
      if (reduceMotion) {
        target.textContent = full;
      } else {
        target.textContent = "";
        var i = 0;
        var step = function () {
          i += 1;
          target.textContent = full.slice(0, i);
          if (i < full.length) {
            window.setTimeout(step, 28);
          } else if (caret) {
            caret.classList.add("caret--blink");
          }
        };
        window.setTimeout(step, 400);
      }
    }
  }

  /* Mobile nav */
  var menuBtn = document.querySelector("[data-menu-toggle]");
  var sheet = document.querySelector("[data-nav-sheet]");
  if (menuBtn && sheet) {
    menuBtn.addEventListener("click", function () {
      var open = menuBtn.getAttribute("aria-expanded") === "true";
      menuBtn.setAttribute("aria-expanded", open ? "false" : "true");
      sheet.classList.toggle("is-open", !open);
    });
    sheet.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        menuBtn.setAttribute("aria-expanded", "false");
        sheet.classList.remove("is-open");
      });
    });
  }

  /* ⌘K palette */
  var palette = document.querySelector("[data-palette]");
  var openers = document.querySelectorAll("[data-palette-open]");
  var input = palette ? palette.querySelector("[data-palette-input]") : null;
  var list = palette ? palette.querySelector("[data-palette-list]") : null;
  var empty = palette ? palette.querySelector("[data-palette-empty]") : null;
  var lastFocus = null;
  var activeIndex = 0;
  var currentFilter = "";
  var onInstallPage =
    document.body && document.body.getAttribute("data-page") === "install";

  var cmdKeys = [
    { id: "demo", key: "cmd.demo", hint: "#demo", href: "#demo" },
    {
      id: "detects",
      key: "cmd.detects",
      hint: "#detecta",
      href: "#detecta",
    },
    { id: "como", key: "cmd.how", hint: "#como", href: "#como" },
    { id: "casos", key: "cmd.cases", hint: "#casos", href: "#casos" },
    {
      id: "instalar",
      key: "cmd.install",
      hint: "install.html",
      href: "install.html",
    },
    { id: "home", key: "cmd.home", hint: "index", href: "index.html" },
    { id: "readme", key: "cmd.readme", hint: "docs", href: "../README.md" },
  ];

  if (onInstallPage) {
    cmdKeys = [
      { id: "home", key: "cmd.home", hint: "index", href: "index.html" },
      { id: "demo", key: "cmd.demo", hint: "index.html#demo", href: "index.html#demo" },
      {
        id: "instalar",
        key: "cmd.install",
        hint: "install.html",
        href: "install.html",
      },
      {
        id: "pasos",
        key: "cmd.install",
        hint: "#pasos",
        href: "#pasos",
      },
      { id: "readme", key: "cmd.readme", hint: "docs", href: "../README.md" },
    ];
  }

  function getCommands() {
    return cmdKeys.map(function (c) {
      var label = typeof siteT === "function" ? siteT(c.key) : c.id;
      return { id: c.id, label: label, hint: c.hint, href: c.href };
    });
  }

  function renderList(filter) {
    if (!list) return;
    currentFilter = filter || "";
    var q = currentFilter.trim().toLowerCase();
    var commands = getCommands();
    var items = commands.filter(function (c) {
      return !q || c.label.toLowerCase().indexOf(q) !== -1 || c.id.indexOf(q) !== -1;
    });
    list.innerHTML = "";
    if (empty) empty.hidden = items.length > 0;
    activeIndex = 0;
    items.forEach(function (cmd, index) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-href", cmd.href);
      if (index === 0) btn.classList.add("is-active");
      btn.innerHTML =
        "<span>" +
        cmd.label +
        '</span><span class="hint">' +
        cmd.hint +
        "</span>";
      btn.addEventListener("click", function () {
        goTo(cmd.href);
      });
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

  document.addEventListener("site:lang", function () {
    if (palette && !palette.hidden && input) renderList(input.value);
    else if (palette && !palette.hidden) renderList(currentFilter);
  });

  function goTo(href) {
    closePalette();
    if (!href) return;
    if (href.charAt(0) === "#") {
      var el = document.querySelector(href);
      if (el) el.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
      return;
    }
    var hashIdx = href.indexOf("#");
    if (hashIdx > 0) {
      var file = href.slice(0, hashIdx);
      var hash = href.slice(hashIdx);
      if (file === (location.pathname.split("/").pop() || "index.html")) {
        var same = document.querySelector(hash);
        if (same) {
          same.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
          return;
        }
      }
    }
    window.location.href = href;
  }

  function openPalette() {
    if (!palette) return;
    lastFocus = document.activeElement;
    palette.hidden = false;
    if (input) {
      input.value = "";
      input.focus();
    }
    renderList("");
  }

  function closePalette() {
    if (!palette) return;
    palette.hidden = true;
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  function moveActive(delta) {
    if (!list) return;
    var buttons = Array.prototype.slice.call(list.querySelectorAll("button"));
    if (!buttons.length) return;
    buttons[activeIndex] && buttons[activeIndex].classList.remove("is-active");
    activeIndex = (activeIndex + delta + buttons.length) % buttons.length;
    buttons[activeIndex].classList.add("is-active");
    buttons[activeIndex].scrollIntoView({ block: "nearest" });
  }

  openers.forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      if (btn.tagName === "A") e.preventDefault();
      openPalette();
    });
  });

  if (palette) {
    palette.addEventListener("click", function (e) {
      if (e.target === palette) closePalette();
    });
  }

  if (input) {
    input.addEventListener("input", function () {
      renderList(input.value);
    });
  }

  document.addEventListener("keydown", function (e) {
    var metaK = (e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K");
    if (metaK) {
      e.preventDefault();
      if (palette && palette.hidden) openPalette();
      else closePalette();
      return;
    }
    if (!palette || palette.hidden) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closePalette();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      moveActive(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      moveActive(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      var active = list && list.querySelector("button.is-active");
      if (active) goTo(active.getAttribute("data-href"));
    }
  });
})();
