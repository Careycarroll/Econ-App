# Econ-App Wireframes

**Status**: Draft — companion to ADR-0003 (Information Architecture)
**Related**: ADR-0001 (Vision & Scope), ADR-0002 (MVP Feature Scope), ADR-0003 (Information Architecture)

---

## Purpose

Low-fidelity ASCII wireframes for each view of the app. These are structural — they show where things live on screen and how views relate to one another. They are not visual mockups; colors, exact spacing, and typography are decided during implementation.

The wireframes below are the visual companion to ADR-0003's structural decisions.

---

## Conventions

- `┌─┐ └─┘` — window/panel edges
- `[ Button ]` — clickable button
- `[▼ Dropdown]` — dropdown/selector
- `☐ / ☑` — checkbox (unchecked / checked)
- `⋮` — content continues (scroll, more items)
- `═` — active/selected state
- `▸ / ▾` — collapsed/expanded tree node

---

## 1. Main Window Shell

The shell is consistent across all views. Only the sidebar contents and content area change.

```
┌─ Econ-App ─────────────────────────────────────────────────────────────────┐
│  Econ-App   View   Data   Window   Help                    (menu bar)      │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐   │
│  │              │  │                                                  │   │
│  │   SIDEBAR    │  │              CONTENT AREA                        │   │
│  │              │  │                                                  │   │
│  │  (contextual │  │        (view-specific content)                   │   │
│  │   content)   │  │                                                  │   │
│  │              │  │                                                  │   │
│  │              │  │                                                  │   │
│  │              │  │                                                  │   │
│  │              │  │                                                  │   │
│  │              │  │                                                  │   │
│  │              │  │                                                  │   │
│  │              │  │                                                  │   │
│  └──────────────┘  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
        280px                          (fills remaining width)
```

**Menu bar**: native on Mac (top of screen), in-window on Windows/Linux.
**Sidebar**: 280px default, draggable divider (200–400px range), toggleable.
**Content area**: fills remaining width; re-flows when sidebar toggles.

---

## 2. Calendar View (Default Landing)

Opens on launch. Investing.com widget embedded in `QWebEngineView`.

```
┌─ Econ-App ─────────────────────────────────────────────────────────────────┐
│  Econ-App   View   Data   Window   Help                                    │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐   │
│  │ [☰] Filters  │  │                                                  │   │
│  │              │  │           ECONOMIC CALENDAR                      │   │
│  │ Country      │  │                                                  │   │
│  │ ☑ United St. │  │   ┌────────────────────────────────────────┐    │   │
│  │ ☐ Canada     │  │   │                                        │    │   │
│  │ ☐ Eurozone   │  │   │      (Investing.com widget)            │    │   │
│  │              │  │   │                                        │    │   │
│  │ Importance   │  │   │   Mon 21     8:30 AM   Housing Starts  │    │   │
│  │ ☐ ★          │  │   │                        Impact: ★★★     │    │   │
│  │ ☐ ★★         │  │   │                                        │    │   │
│  │ ☑ ★★★        │  │   │   Tue 22     8:30 AM   CPI             │    │   │
│  │              │  │   │                        Impact: ★★★     │    │   │
│  │ Categories   │  │   │                                        │    │   │
│  │ ☑ Labor      │  │   │   Wed 23     10:00 AM  Existing Home   │    │   │
│  │ ☑ Prices     │  │   │                        Sales           │    │   │
│  │ ☑ GDP        │  │   │                        Impact: ★★      │    │   │
│  │ ☑ Housing    │  │   │                                        │    │   │
│  │ ☐ Other      │  │   │   ⋮                                    │    │   │
│  │              │  │   │                                        │    │   │
│  │ Date Range   │  │   └────────────────────────────────────────┘    │   │
│  │ [▼ This Wk]  │  │                                                  │   │
│  │              │  │                                                  │   │
│  └──────────────┘  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

**Sidebar (Filters)**:
- **Country** — checkboxes. U.S. only by default.
- **Importance** — 1/2/3 star checkboxes. ★★★ only by default.
- **Categories** — Labor, Prices, GDP, Housing, Other. All on by default.
- **Date Range** — dropdown: Today, This Week, Next Week, Custom.

Filter changes update the widget URL (if the widget supports it) or apply post-widget filtering. Some filters may be no-ops depending on widget capabilities; those get cut if they don't work.

**Content area**: full-widget calendar. No chart controls (this is not a chart view).

**Deep linking**: clicking a release *may* navigate to the corresponding Series Detail (feature 1.5, Should — deferred to post-v1 unless implementation is trivial).

---

## 3. Explorer View

Browse the FRED Core Catalog by category → release → series.

```
┌─ Econ-App ─────────────────────────────────────────────────────────────────┐
│  Econ-App   View   Data   Window   Help                                    │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐   │
│  │ [☰] Explorer │  │                                                  │   │
│  │              │  │  Category: Labor Markets                         │   │
│  │ 🔍 Search... │  │                                                  │   │
│  │              │  │  ┌────────────────────────────────────────────┐  │   │
│  │ ▾ Labor      │  │  │  Employment Situation                      │  │   │
│  │   ▸ Employ.  │  │  │  BLS · Monthly · First Friday 8:30 AM ET   │  │   │
│  │   ▸ JOLTS    │  │  │  Impact: Stocks ★★★  Bonds ★★★  $ ★★★     │  │   │
│  │   ▸ Claims   │  │  │  Series: PAYEMS, UNRATE, AHETPI...         │  │   │
│  │              │  │  └────────────────────────────────────────────┘  │   │
│  │ ▸ Prices     │  │                                                  │   │
│  │ ▸ GDP        │  │  ┌────────────────────────────────────────────┐  │   │
│  │ ▸ Consumer   │  │  │  JOLTS                                     │  │   │
│  │ ▸ Housing    │  │  │  BLS · Monthly · ~5 weeks after month end   │  │   │
│  │ ▸ Business   │  │  │  Impact: Stocks ★  Bonds ★★  $ ★           │  │   │
│  │ ▸ Fed        │  │  │  Series: JTSJOL, JTSQUL, JTSHIL...         │  │   │
│  │ ▸ Banking    │  │  └────────────────────────────────────────────┘  │   │
│  │ ▸ Fin. Cond. │  │                                                  │   │
│  │ ▸ Trade      │  │  ┌────────────────────────────────────────────┐  │   │
│  │ ▸ Fiscal     │  │  │  Weekly Unemployment Claims                │  │   │
│  │ ▸ Energy     │  │  │  DOL · Weekly · Thursday 8:30 AM ET        │  │   │
│  │              │  │  │  Impact: Stocks ★★  Bonds ★★  $ ★          │  │   │
│  └──────────────┘  │  │  Series: ICSA, CCSA                        │  │   │
│                    │  └────────────────────────────────────────────┘  │   │
│                    │                                                  │   │
│                    └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

**Sidebar (Navigation Tree)**:
- **Search box** at top — flat search across all series by name or ID.
- **Category tree** — 12 top-level categories, expandable to releases, expandable to series.
- Currently selected node highlighted; content area reflects current position.

**Content area**:
- Header shows current selected category
- Grid of release cards for that category
- Each card shows: release name, source + schedule, market impact badges, sample series
- Click a card → navigates to that release's series list (nested inside Explorer)
- Click a series → Series Detail view

**No chart here** — Explorer is for browsing, not viewing.

---

## 4. Series Detail View

The primary "look at data" view. Single scrollable page.

```
┌─ Econ-App ─────────────────────────────────────────────────────────────────┐
│  Econ-App   View   Data   Window   Help                                    │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐   │
│  │ [☰] Explorer │  │  ← Back to Explorer                              │   │
│  │              │  │                                                  │   │
│  │ 🔍 Search... │  │  Consumer Price Index (CPIAUCSL)                 │   │
│  │              │  │  Source: BLS via FRED · Last updated: 2026-07-15 │   │
│  │ ▾ Prices     │  │  Next release: 2026-08-13 (Aug CPI)              │   │
│  │   ═ CPI      │  │                                                  │   │
│  │   ▸ Core CPI │  │  Impact:  📈 Stocks ★★★   💵 Bonds ★★★   $ ★★★  │   │
│  │   ▸ PPI      │  │                                                  │   │
│  │   ▸ PCE      │  │  ┌────────────────────────────────────────────┐  │   │
│  │              │  │  │  [Level] [YoY %] [MoM %] [QoQ] [Annlz]     │  │   │
│  │ ▸ Labor      │  │  │  [1Y] [5Y] [10Y] [MAX] [Custom▼]           │  │   │
│  │ ▸ GDP        │  │  │  [+ Compare]  ☐ Recession shading          │  │   │
│  │ ▸ Consumer   │  │  └────────────────────────────────────────────┘  │   │
│  │ ▸ Housing    │  │                                                  │   │
│  │ ▸ Business   │  │  ┌────────────────────────────────────────────┐  │   │
│  │ ▸ Fed        │  │  │                                            │  │   │
│  │ ⋮            │  │  │           (PyQtGraph chart)                │  │   │
│  │              │  │  │                                            │  │   │
│  │              │  │  │       ╱╲    ╱╲                             │  │   │
│  │              │  │  │      ╱  ╲  ╱  ╲    ╱╲                      │  │   │
│  │              │  │  │  ___╱    ╲╱    ╲__╱  ╲__                   │  │   │
│  │              │  │  │                                            │  │   │
│  │              │  │  │  2020        2022        2024        2026  │  │   │
│  │              │  │  │                                            │  │   │
│  │              │  │  └────────────────────────────────────────────┘  │   │
│  └──────────────┘  │                                                  │   │
│                    │  About this series                               │   │
│                    │  ─────────────────────────────                   │   │
│                    │  One-sentence: The headline U.S. inflation       │   │
│                    │  measure, tracking prices paid by urban          │   │
│                    │  consumers for a fixed basket of goods and       │   │
│                    │  services.                                       │   │
│                    │                                                  │   │
│                    │  Overview                                        │   │
│                    │  ─────────                                       │   │
│                    │  CPIAUCSL is the seasonally-adjusted Consumer    │   │
│                    │  Price Index for All Urban Consumers...          │   │
│                    │                                                  │   │
│                    │  What it measures                                │   │
│                    │  ─────────────────                               │   │
│                    │  ⋮                                               │   │
│                    │                                                  │   │
│                    │  Why it matters                                  │   │
│                    │  ────────────────                                │   │
│                    │  ⋮                                               │   │
│                    │                                                  │   │
│                    │  Release schedule                                │   │
│                    │  ─────────────────                               │   │
│                    │  Monthly, second Tuesday, 8:30 AM ET.            │   │
│                    │  Covers the prior calendar month.                │   │
│                    │                                                  │   │
│                    └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

**Sidebar**: same navigation tree as Explorer, but current series is highlighted. User can jump to related series without leaving Series Detail.

**Content area** (single scrollable page, top-to-bottom):

1. **Back link** — returns to Explorer at the current node
2. **Title + metadata line** — series name, ID, source, last updated, next release
3. **Market impact badges** — Stocks / Bonds / Dollar star ratings from Baumohl framework
4. **Chart controls row**:
   - Transform selector (Level / YoY % / MoM % / QoQ / Annualized) — currently-selected highlighted
   - Date range presets (1Y / 5Y / 10Y / MAX) + Custom picker
   - "+ Compare" button — expands compare mode inline (see below)
   - Recession shading toggle (Should, likely v1.1)
5. **Chart** — PyQtGraph line chart, ~500px tall, fills width. Interactive pan/zoom/crosshair.
6. **Learning content** (below chart, all visible on scroll):
   - One-sentence definition
   - Overview paragraph
   - "What it measures"
   - "Why it matters"
   - Release schedule

Progressive disclosure of tiers (feature 6.2) is Should, not Must — v1 shows all three tiers stacked with clear section headings. User scrolls past what they don't need.

---

### 4a. Series Detail — Compare Mode

Clicking "+ Compare" expands controls inline above the chart. Same view, expanded state.

```
                    │  Chart controls (with compare expanded):         │
                    │  ┌────────────────────────────────────────────┐  │
                    │  │  Primary:   CPIAUCSL — Consumer Price Idx  │  │
                    │  │  Transform: [Level] [YoY %] [MoM %] [QoQ]  │  │
                    │  │  Range:     [1Y] [5Y] [10Y] [MAX]          │  │
                    │  │                                            │  │
                    │  │  Compare with:                             │  │
                    │  │  [+ CPILFESL — Core CPI       ] [ × ]      │  │
                    │  │  [+ PCEPI — PCE               ] [ × ]      │  │
                    │  │  [+ Add another (max 4 total) ]            │  │
                    │  │                                            │  │
                    │  │  ☐ Recession shading                       │  │
                    │  └────────────────────────────────────────────┘  │
                    │                                                  │
                    │  ┌────────────────────────────────────────────┐  │
                    │  │  (Chart with multiple series overlaid)     │  │
                    │  │                                            │  │
                    │  │  Legend:                                   │  │
                    │  │  ─── CPI (3.2% YoY)                        │  │
                    │  │  ─── Core CPI (3.4% YoY)                   │  │
                    │  │  ─── PCE (2.9% YoY)                        │  │
                    │  └────────────────────────────────────────────┘  │
```

- Transform is shared across compared series (same-unit overlay, Must)
- Max 3–4 total series to keep readable (feature 4.9)
- Legend shows color + name + current value (feature 4.10)
- Dual-axis and scatter/correlation modes are Should — deferred to v1.1+

---

## 5. Core Indicators View

Curated view based on Baumohl's Tables 1B, 1C, 1D, 1E from *The Secrets of Economic Indicators*, Ch. 1.

```
┌─ Econ-App ─────────────────────────────────────────────────────────────────┐
│  Econ-App   View   Data   Window   Help                                    │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐   │
│  │ [☰] Filter   │  │  Core Indicators                                 │   │
│  │              │  │                                                  │   │
│  │ Market       │  │  📈 Top 10 for Stocks                            │   │
│  │ ○ All        │  │  ────────────────────────                        │   │
│  │ ● Stocks     │  │  ┌─────────────────┐ ┌─────────────────┐         │   │
│  │ ○ Bonds      │  │  │ Employment      │ │ ISM Manufact.   │         │   │
│  │ ○ Dollar     │  │  │ Situation       │ │ PMI             │         │   │
│  │ ○ Leading    │  │  │ ★★★             │ │ ★★★             │         │   │
│  │              │  │  └─────────────────┘ └─────────────────┘         │   │
│  │              │  │                                                  │   │
│  │              │  │  ┌─────────────────┐ ┌─────────────────┐         │   │
│  │              │  │  │ Weekly Claims   │ │ Consumer Prices │         │   │
│  │              │  │  │ ★★★             │ │ ★★★             │         │   │
│  │              │  │  └─────────────────┘ └─────────────────┘         │   │
│  │              │  │                                                  │   │
│  │              │  │  ⋮                                               │   │
│  │              │  │                                                  │   │
│  └──────────────┘  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

**Sidebar**: radio buttons for market filter (Stocks / Bonds / Dollar / Leading / All).

**Content area**: series cards grouped by market. Click card → Series Detail.

Access:
- View menu → Core Indicators (⌘4)
- Not currently in main sidebar tree; may be added later if we find it's used often

---

## 6. Preferences Dialog (Modal)

Native OS dialog. Not part of primary navigation.

```
┌─ Preferences ─────────────────────────────────────────┐
│                                                       │
│  [General]  [Appearance]  [Data]  [Advanced]          │
│                                                       │
│  ─── Appearance ────────────────────────────────────  │
│                                                       │
│  Font size                                            │
│  Small ─────●────────── Large    (Currently: 12pt)   │
│  [⌘+ / ⌘- to adjust on the fly]                       │
│                                                       │
│  Sidebar default state                                │
│  ● Open   ○ Closed                                    │
│                                                       │
│  Compact mode                                         │
│  ☐ Reduce padding in lists and sidebars               │
│                                                       │
│  Theme (v1.1+)                                        │
│  [▼ System default (dark/light auto)]                 │
│                                                       │
│                                                       │
│                                       [Cancel] [OK]   │
└───────────────────────────────────────────────────────┘
```

**Tabs**:
- **General** — default view on launch (Calendar)
- **Appearance** — font size, sidebar default, compact mode, theme (v1.1+)
- **Data** — FRED API key management, data folder location, refresh preferences
- **Advanced** — log level, reset to defaults

Access: menu bar → Preferences (⌘,)

---

## Focus Mode Behavior

Not a view — a *mode* applied to any current view. Toggled via **View → Focus Mode** (⌘⇧F).

### When Focus Mode is active

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│                   (Sidebar hidden, menu bar hidden — Mac only)             │
│                                                                            │
│                        Consumer Price Index (CPIAUCSL)                    │
│                        Source: BLS via FRED                                │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  [Level] [YoY %] [MoM %]   [1Y] [5Y] [10Y] [MAX]                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │                        (Chart fills the screen)                      │  │
│  │                                                                      │  │
│  │             ╱╲    ╱╲                                                 │  │
│  │            ╱  ╲  ╱  ╲                                                │  │
│  │        ___╱    ╲╱    ╲___                                            │  │
│  │                                                                      │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│                            (learning content below scrolls into view)      │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**What's hidden**:
- Sidebar
- Menu bar (Mac: true fullscreen; Win/Linux: minimized)
- Preferences dialog (closes if open)

**What stays**:
- Chart controls (transform, date range) — you're focused on the chart, not away from it
- Chart itself
- Learning content

**Exit paths**:
- ⌘⇧F toggles off
- Esc key exits
- Move mouse to top of screen briefly reveals menu bar (standard Mac fullscreen)

**Auto-exit conditions**:
- Switching views (⌘1–4)
- Opening any dialog (Preferences, About, etc.)

---

## Sidebar Layout Pattern

The sidebar uses **push (reflow)** behavior — it is part of the layout, not an overlay.

### Behavior details

- **Divider is draggable** — user can resize sidebar between 200px (min) and 400px (max)
- **State persisted** — open/closed and width remembered across sessions
- **Animation** — ~150ms slide when toggling
- **Chart re-flows** when sidebar toggles — this is expected; the chart uses available width

### Why push (not overlay)

- Charts benefit from full width; overlay would cover chart content
- Sidebar content is functional (filters, navigation), not "peek at then dismiss"
- Matches productivity app conventions (VS Code, Slack, Figma, Bloomberg)

### Not in v1: rail mode

A "rail" state (collapsed-to-icons-only, ~50px wide) was considered. Standard modern pattern (VS Code, Figma, Linear), but adds complexity in exchange for marginal gain in a personal tool. Candidate for v1.1 if push-only feels too binary in practice.

---

## Font Size and Compact Mode

### Font size

- Slider in **Preferences → Appearance** sets base font size (Small / Medium / Large or specific pt values)
- Keyboard shortcuts adjust on the fly:
  - **⌘+** increase font size
  - **⌘-** decrease font size
  - **⌘0** reset to default
- All UI text respects the setting — sidebar, content, chart labels, learning content

### Compact mode

- Optional toggle in **Preferences → Appearance**
- Reduces padding in lists, cards, and sidebar entries
- Font size unchanged; only spacing tightens
- Useful for dense information display without shrinking readable text
- Off by default

---

## What's Explicitly *Not* Shown

- **Detailed styling** — colors, typography, exact spacing decided at implementation time
- **Loading states** — spinners/skeletons handled during build
- **Error states** — toast notifications (feature 9.10); design in implementation
- **Empty states** — "no results," "cache empty," etc.
- **Drag-and-drop interactions** — none in v1 scope
- **Right-click / context menus** — none in v1 scope

These are all v1 concerns but not IA-level decisions. They belong in visual design or component-level specs, not here.
