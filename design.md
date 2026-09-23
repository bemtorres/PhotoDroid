# Design — PhotoDroid

Locked design system for the desktop app UI. Read before emitting app chrome.
`designed-as-app` · genre modern-minimal · mood macOS.

## Genre
modern-minimal (soft / utilitarian)

## Macrostructure family
- App pages: **Workbench** — fixed sidebar rail + toolbar + scrollable content panes.
  Knobs: card density, table vs empty-state, toolbar actions.

## Theme — macOS Aqua (light)
- `--color-paper`     oklch(96.5% 0.004 250)
- `--color-paper-2`   oklch(93.5% 0.006 250)   /* sidebar / chrome */
- `--color-paper-3`   oklch(90% 0.007 250)     /* sunken wells */
- `--color-surface`   oklch(99% 0.002 250)     /* cards */
- `--color-ink`       oklch(22% 0.01 255)
- `--color-ink-2`     oklch(42% 0.01 255)
- `--color-muted`     oklch(55% 0.01 255)
- `--color-rule`      oklch(88% 0.005 255)
- `--color-accent`    oklch(54% 0.16 250)      /* system blue */
- `--color-accent-ink` oklch(98% 0.005 250)
- `--color-focus`     oklch(54% 0.16 250)
- Semantic: success oklch(52% 0.12 155) · warning oklch(58% 0.14 75) · danger oklch(52% 0.18 25)

Accent ≤ 5% viewport. No pure #000 / #fff. No glassmorphism (genre ban).
No re-drawn traffic lights or fake window chrome.

## Typography
- Display / body: **Geist** (Google Fonts), 400 / 500 / 600 / 700
- Mono (logs, package ids): **Geist Mono** / system mono fallback
- Display tracking: `-0.02em` · body line-height 1.5
- Scale: major third 1.25 from 13–14px app body (desktop density)
- All headings roman (no italics)

## Spacing
4-pt scale: 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40
Named: `--space-1`…`--space-8` in `app.css`.

## Motion
- `--ease-out: cubic-bezier(0.2, 0.8, 0.2, 1)` · `--dur: 180ms`
- Transitions on hover/active only. No scroll reveals.
- Reduced motion: opacity ≤ 150ms.

## Microinteractions
- Hover delay 0 · focus-visible ring 2px accent
- Selection: soft accent-tint pill (Finder-like), never full-bleed accent fills
- Busy: buttons dimmed (`disabled`), cancel stays live during scan

## CTA voice
- Primary: filled system-blue, radius 8px, height 32–36px, Geist 500
- Secondary: paper-2 fill + hairline rule, ink text
- Danger: danger fill or tinted rose text on secondary

## Per-page allowances
- App pages MUST NOT use marketing enrichment — function only.
- Tables: sticky header row, hairline separators, mono for package/PID.

## What pages MUST share
- Sidebar rail, header toolbar, card surface language, accent placement,
  Geist pair, button voice, table density.

## What pages MAY differ on
- Content composition inside main pane only (cards / tables / empty states).
