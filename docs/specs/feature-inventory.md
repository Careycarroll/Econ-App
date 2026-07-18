# Feature Inventory

**Status**: Draft — for MoSCoW prioritization in ADR-0002
**Related**: ADR-0001 (Vision & Scope), use-cases.md

---

## Purpose

Exhaustive menu of every feature the app **could** have. Prioritization comes later (ADR-0002 will apply MoSCoW to this list). Right now this is just the option set — comprehensive, unfiltered, with no implied commitment.

For each feature, the user (Carey) will mark:

- **M** — Must have for v1. Without this, the app doesn't satisfy the core use cases.
- **S** — Should have. Important, but v1 could ship without it.
- **C** — Could have. Nice, if there's time and it doesn't add complexity.
- **W** — Won't have (this time). Deferred to v2+ or explicitly rejected.

Blank = not yet decided.

---

## 1. Calendar

Anchor of the app; the default landing view per ADR-0001.

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 1.1 | Embed Investing.com calendar widget in a `QWebEngineView` | M | Recommended v1 approach |
| 1.2 | Filter widget to U.S. only by default | S | |
| 1.3 | Filter widget to high-importance events by default | S | |
| 1.4 | Configurable timezone (default: user's local; option: ET) | C | |
| 1.5 | Deep-link from calendar event → matching chart in app | S | Requires event → series mapping; harder |
| 1.6 | Build our own calendar UI (defer per ADR-0001) | W | v2+ |
| 1.7 | Calendar reminders / notifications for high-impact releases | C | |
| 1.8 | Export calendar as ICS for OS calendar sync | C | |
| 1.9 | Custom event annotations ("watch core services") | C | |
| 1.10 | Historical view of past releases (what came out when) | C | |

---

## 2. Category & Series Navigation

How the user finds a series to view.

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 2.1 | Sidebar with 12 top-level categories (Labor, Prices, GDP, etc.) | M | |
| 2.2 | Expand category → releases within that category | M | |
| 2.3 | Expand release → series within that release | M | |
| 2.4 | Flat search across all series by name or ID | M | |
| 2.5 | "Favorites" list for pinned series | S | |
| 2.6 | "Recently viewed" list | C | |
| 2.7 | Filter categories by relevance to user (hide categories) | W | v2+ |
| 2.8 | Custom user-defined categories or tags | W | v2+ |
| 2.9 | Series list shows current value + last-updated inline | S | |
| 2.10 | Sortable series list (by name, last update, importance) | C | |

---

## 3. Chart Viewing

The primary "explore" experience.

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 3.1 | Single-series line chart via PyQtGraph | M | Core |
| 3.2 | Interactive pan and zoom | M | PyQtGraph native |
| 3.3 | Crosshair with tooltip showing date + value | M | PyQtGraph native |
| 3.4 | Date range picker (preset: 1Y, 5Y, 10Y, MAX + custom) | M | |
| 3.5 | Transform selector (Level, YoY %, MoM %, QoQ %, Annualized) | M | Some transforms only apply to certain series |
| 3.6 | Log/linear y-axis toggle | C | |
| 3.7 | Recession shading (NBER-defined) overlay toggle | S | |
| 3.8 | Grid lines toggle | C | |
| 3.9 | Chart title, subtitle, axis labels auto-populated from catalog | M | |
| 3.10 | Attribution/source line ("Source: BLS via FRED") | M | |
| 3.11 | Last-updated timestamp on chart | M | |
| 3.12 | Data table view (raw values) alongside chart | C | |
| 3.13 | Chart export as PNG/SVG image | S | |
| 3.14 | Data export as CSV | S | |

---

## 4. Correlation & Comparison

Overlaying two or more series to see relationships.

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 4.1 | "+ Compare" button to add second series to current chart | M | |
| 4.2 | Same-unit overlay (both series on shared axis, e.g., CPI vs Core CPI) | M | |
| 4.3 | Rebased-to-100 mode (normalize to common start date) | S | |
| 4.4 | Dual y-axis mode (different units on left/right) | S | With scaling caveat |
| 4.5 | Scatter plot mode with correlation coefficient (r) | S | |
| 4.6 | Rolling correlation over time (e.g., 12-month rolling r) | C | |
| 4.7 | Difference/spread line (A − B) | S | e.g., 10Y-2Y yield curve |
| 4.8 | Lead/lag adjustment control (shift one series by N periods) | W | v2+ likely |
| 4.9 | Cap on overlay count (3–4 max for readability) | M | UX guardrail |
| 4.10 | Legend with color, series name, current value | M | |

---

## 5. Market Impact & Core Indicator Metadata

Per Baumohl's *The Secrets of Economic Indicators* Ch. 1 ("The Lock-Up"). Directly serves UC-1, UC-2, UC-3, UC-5.

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 5.1 | Tag each series with market impact: Stocks, Bonds, Dollar, All, None | M | |
| 5.2 | Tag each series with importance rank within its market (1–10) | S | Baumohl provides rankings |
| 5.3 | Flag "leading indicator" series | S | Baumohl Table 1E |
| 5.4 | Filter series list by market impact | S | e.g., "show me all bond-sensitive indicators" |
| 5.5 | Display market impact on chart page (badges/pills) | M | |
| 5.6 | "Core Indicators" curated view — Baumohl's top-10 stocks / top-10 bonds / top-10 dollar | M | |
| 5.7 | Show "typical market reaction" note on each series page | S | |
| 5.8 | Business cycle stage tagging (recession-sensitive vs expansion-sensitive) | C | |

---

## 6. Learning Content

Making the app teach the user, not just display data. Per UC-3.

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 6.1 | Three-tier explanations per series (sentence / paragraph / detailed) | M | Format already established in FRED Core Catalog |
| 6.2 | Progressive disclosure — user chooses tier | S | |
| 6.3 | "What it measures" section | M | |
| 6.4 | "How it's constructed" section (methodology) | S | |
| 6.5 | "Why it matters" section (market/policy impact) | M | |
| 6.6 | "Typical transform" recommendation | S | |
| 6.7 | "Common pitfalls" section | S | |
| 6.8 | "Related series" cross-links | S | |
| 6.9 | Release schedule (frequency, day/time) | M | |
| 6.10 | Link to source's official release page | S | |
| 6.11 | Link to FRED series page | S | |
| 6.12 | Glossary of economic terms (accessible from any page) | C | |
| 6.13 | Inline term tooltips (hover over "core inflation" → definition) | W | v2+ |
| 6.14 | "Learn more" links to FRED blog posts, agency methodology docs | C | |

---

## 7. Data Management

How the app gets and stores data from FRED.

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 7.1 | FRED API client with API key from `.env` | M | |
| 7.2 | Local SQLite cache for series observations | M | |
| 7.3 | Local CSV archive of downloaded data | S | Per your earlier requirement |
| 7.4 | Manual "refresh" button per series | M | |
| 7.5 | Manual "refresh all" for catalog series | S | |
| 7.6 | Scheduled/automatic refresh (daily at 5 PM ET?) | C | |
| 7.7 | Show "last synced" timestamp | M | |
| 7.8 | Show "next expected release" (from catalog metadata) | S | |
| 7.9 | Handle FRED rate limits gracefully | M | 120/min is easy for personal use |
| 7.10 | Handle offline mode (use cache when no network) | S | |
| 7.11 | Data revision tracking (compare vintages) | W | v2+ |
| 7.12 | Export entire local cache for backup | C | |

---

## 8. Configuration & Preferences

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 8.1 | FRED API key management (`.env` file) | M | |
| 8.2 | API key stored in OS keyring (more secure) | S | |
| 8.3 | Preferences UI for defaults (date range, transform, timezone) | S | |
| 8.4 | Choose light/dark theme | C | |
| 8.5 | Choose data directory location | C | |
| 8.6 | Log level control (Debug/Info/Warn/Error) | C | |
| 8.7 | Reset app to defaults | C | |
| 8.8 | Auto-launch on system startup option | W | |

---

## 9. UI Framework & Polish

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 9.1 | Native PySide6 (Qt) window with menu bar | M | |
| 9.2 | Resizable panes (sidebar + main content) | M | |
| 9.3 | Remembers window size/position across sessions | S | |
| 9.4 | Keyboard shortcuts (Cmd+F search, Cmd+, preferences) | S | |
| 9.5 | Cross-platform: macOS, Windows, Linux | M | |
| 9.6 | Dark mode | C | |
| 9.7 | Custom app icon | C | |
| 9.8 | Splash screen on launch | W | v2+ |
| 9.9 | Loading indicators for slow operations | M | |
| 9.10 | Error/toast notifications | M | |

---

## 10. Distribution & Ops

| # | Feature | M/S/C/W | Notes |
|---|---|---|---|
| 10.1 | Run from source (`python app.py`) | M | |
| 10.2 | PyInstaller bundle for macOS | S | |
| 10.3 | PyInstaller bundle for Windows | S | |
| 10.4 | PyInstaller bundle for Linux | S | |
| 10.5 | Signed macOS build (Gatekeeper compliance) | W | v2+ |
| 10.6 | Auto-update mechanism | W | v2+ |
| 10.7 | Crash reporting | W | v2+ |

---

## 11. Reserved for Future (v2+)

Features explicitly noted as "not v1" so they're captured but not on the table for MoSCoW:

- Multi-view dashboards (2x2 or 3x3 chart grids)
- Custom user annotations on charts (arrows, text, event markers)
- Import external data (CSV/Excel) alongside FRED series
- Series bookmarking with notes
- Time-machine mode (view what the data looked like as of a past date)
- International data expansion beyond U.S.
- Mobile companion (iOS/Android) — unlikely given desktop-first vision
- Report parsing / auto-summarization
- LLM-powered "explain this chart" feature
- Statistical tests (cointegration, Granger causality)

---

## How to Use This Document

1. **Read through once** to see the full menu.
2. **Do a first pass** marking each item M/S/C/W based on gut reaction.
3. **Reference `use-cases.md`** — for each feature, ask: does it serve UC-1 through UC-5?
4. **Iterate** — the marks aren't final until ADR-0002.
5. **Flag anything missing** — if a feature you want isn't listed, add it before locking.

The output of this exercise becomes the basis for ADR-0002 (MVP Feature Scope), which locks the v1 build scope.
