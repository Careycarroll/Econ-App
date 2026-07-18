# ADR-0003: Information Architecture

**Status**: Accepted
**Date**: 2026-07-18
**Deciders**: Carey Carroll
**Supersedes**: None
**Related**: ADR-0001 (Vision & Scope), ADR-0002 (MVP Feature Scope), ADR-0004 (Technology Stack), `docs/specs/wireframes.md`

---

## Context

ADR-0001 established the vision. ADR-0002 locked v1 scope (36 Musts). ADR-0004 locked the stack (PySide6 + PyQtGraph). What remains before writing code is a decision about **how the app is organized** — what pages exist, how the user navigates, where content lives on screen, and how the shell behaves.

Without this ADR, every UI-related engineering task becomes an open question: "Where does the Compare button live?" "Does the sidebar close when I click a series?" "Where do settings live?" These questions are answered here, once, so implementation is a matter of building to the spec rather than re-designing during the build.

Wireframes in `docs/specs/wireframes.md` are the visual companion. This ADR captures the *decisions* the wireframes imply, with rationale, so future changes can reference "why."

---

## Decision

### The App Shell

A single main window with three permanent regions:

| Region | Purpose |
|---|---|
| **Menu bar** | App-level navigation and global actions. Native on Mac (top of screen), in-window on Windows/Linux via `QMenuBar` |
| **Sidebar** | Contextual — content changes based on active view |
| **Content area** | The primary view (Calendar, Explorer, Series Detail, Core Indicators) |

No status bar in v1 (deferred; would only add clutter without earning its keep).

### The Four Primary Views

The app has **four primary content views** plus one **Preferences dialog**:

1. **Calendar** — the default landing view. Investing.com widget embedded in `QWebEngineView`. Sidebar shows filters (country, importance, categories, date range).
2. **Explorer** — browse the FRED Core Catalog. Sidebar shows Category → Release → Series navigation tree. Content shows the currently-selected category's release list.
3. **Series Detail** — the deep-dive on one series. Chart, controls (transform, date range, compare), market impact badges, learning content. Sidebar keeps navigation tree so user can jump around.
4. **Core Indicators** — Baumohl's top-10 lists (Stocks / Bonds / Dollar / Leading). Sidebar shows category filters. Content shows curated series cards.

**Preferences** is a modal dialog (not a view) accessed via menu bar (⌘,). Standard OS convention.

### Menu Bar Structure

Six menus:

| Menu | Contents |
|---|---|
| **Econ-App** (Mac) / **File** (Win/Linux) | About, Preferences (⌘,), Quit (⌘Q) |
| **View** | Calendar (⌘1), Explorer (⌘2), Series Detail (⌘3), Core Indicators (⌘4), Toggle Sidebar (⌘\\), Focus Mode (⌘⇧F), Zoom In / Reset / Out (⌘+ / ⌘0 / ⌘-) |
| **Data** | Refresh All (⌘R), Refresh Current Series, Open Data Folder |
| **Window** | Minimize, Zoom (standard Qt/Mac window management) |
| **Help** | FRED Documentation, About FRED Series IDs, Report Issue |

Menu bar handles *global* actions. In-view controls handle *content-specific* actions (transform selector, date range picker, compare button, etc.). Clear separation.

### Sidebar Behavior

**Layout**: Push (reflow), not overlay. When open, sidebar occupies real screen space; when closed, content area expands. Chart re-flows on toggle.

**States**:
- **Open** (default): 280px wide, resizable via drag divider (200-400px range)
- **Closed**: hidden, content area takes full width
- **Toggle**: button top-left in every view, plus ⌘\\ keyboard shortcut

**Contextual content** based on active view:

| View | Sidebar Shows |
|---|---|
| Calendar | Filters: country checkboxes, importance stars, category checkboxes, date range |
| Explorer | Navigation tree: Category → Release → Series (expandable) |
| Series Detail | Navigation tree (same as Explorer — for jumping around) |
| Core Indicators | Filters: Stocks / Bonds / Dollar / Leading / All |

**Persistence**: sidebar open/closed state and width remembered across sessions. Per-window, not per-view (one global setting).

**Not in v1**: Rail mode (collapsed-to-icons state). Considered — good pattern (VS Code, Figma) — but adds complexity for marginal gain in a personal tool. Candidate for v1.1 if push-only feels too binary in practice.

### Focus Mode

Removes navigation chrome to maximize chart/content readability. Accessed via **View → Focus Mode** (⌘⇧F).

**When active**:
- Sidebar hidden
- Menu bar hidden on Mac (true fullscreen); minimized on Windows/Linux
- Preferences dialog closes if open
- **Chart controls remain visible** — Focus Mode is about removing distraction, not core interactions

**Exit paths**: ⌘⇧F toggles off, Esc key exits, moving mouse to top of screen briefly reveals menu bar (standard Mac fullscreen convention).

**Auto-exit conditions**: switching views (⌘1-4) or opening any dialog automatically exits Focus Mode.

Not expected to be heavily used — included because it's small effort and matches modern app conventions (Zen browser, IDE zen modes).

### Navigation Model

Three overlapping navigation mechanisms, each serving a different mode:

**1. Menu bar** — jump to any view directly (⌘1-4). Global commands (refresh, preferences, quit).

**2. Sidebar** — contextual within a view:
- Calendar: filter what's visible
- Explorer/Series Detail: browse the catalog tree
- Core Indicators: filter the curated list

**3. In-view interactions** — click a category card in Explorer to see its releases; click a release to see its series; click a series to go to Series Detail. Click a calendar event (if event → series mapping exists) to jump to that Series Detail.

**Not doing breadcrumbs in v1.** The sidebar tree makes hierarchy visible enough. Breadcrumbs would be redundant and add chrome. Reconsider in v1.1 if the tree feels insufficient.

**Deep-linking from calendar events** (feature 1.5, marked Should in ADR-0002): requires event → series ID mapping. Complexity varies by widget capabilities. Deferred to post-v1 unless implementation turns out trivial.

### Layout of Each View

Detailed layouts live in `docs/specs/wireframes.md`. Structural principles per view:

**Calendar**
- Full-content-area embedded widget
- Sidebar: filters affecting widget URL (if supported) or post-widget rendering
- No chart controls (Calendar is not a chart view)

**Explorer**
- Content area shows category cards (grid) → release list → series list
- Progressive drill-down; sidebar tree mirrors current position
- No chart shown — Explorer is for browsing, not viewing

**Series Detail** (the primary "explore data" view)
- Single scrollable page, top-to-bottom:
  1. Series title + metadata line (source, last updated, next expected release)
  2. Market impact badges (Stocks / Bonds / Dollar / Leading indicators from ADR-0002 §5)
  3. Chart controls row (transform selector, date range picker, compare button, recession toggle if applicable)
  4. Chart (fills available width; sized to look good at ~500px tall)
  5. Learning content: three-tier explanations, "What it measures," "Why it matters," release schedule
- Compare mode expands controls inline above chart (not a separate view)
- Single scrollable page chosen over tabs (Chart | Learning | Data) for simplicity — a personal tool doesn't need progressive disclosure of learning material; user can just scroll past it

**Core Indicators**
- Content area shows curated series as cards
- Cards grouped by market: Stocks, Bonds, Dollar, Leading Indicators (from Baumohl Tables 1B, 1C, 1D, 1E)
- Click card → Series Detail for that series
- Sidebar filter: which market to show

### Preferences Dialog

Modal, accessed via menu bar (⌘,). Native OS dialog styling. Not part of primary navigation.

**Sections** (as tabs within the dialog):

| Tab | Contents |
|---|---|
| **General** | Default view on launch (currently Calendar) |
| **Appearance** | Font size slider (Small / Medium / Large + specific pt values), compact mode toggle, sidebar default state |
| **Data** | FRED API key (from `.env`; UI shows masked value with "Change..." button that opens `.env`), data directory location, refresh cadence hint |
| **About** | Version, credits, links |

Keyboard shortcuts (⌘+, ⌘-, ⌘0) also adjust font size at runtime for quick tweaks without opening Preferences.

### Persisted UI State

The following state persists across app launches (stored in a settings file or OS preferences):

- Sidebar open/closed state and width
- Font size preference
- Compact mode toggle
- Last-selected view (or user-set default)
- Window size and position
- Calendar filter selections
- Series Detail default transform (per-series or global?)

**Decision**: default transform is *global*, not per-series. Simpler. Per-series can be added in v1.1 if a real need emerges. (For example, one might always want CPI in YoY %; per-series preferences would remember that.)

### Categories and Terminology

Categories used in the sidebar navigation tree (Labor, Prices, GDP, Consumer, Housing, Business, Financial, Trade) are the ones from `docs/reference/fred-core-catalog.md`. This ADR does **not** finalize the category taxonomy — that happens when the catalog is fully populated. Wireframes and IA use these placeholders because they're representative.

The 12-category number cited in ADR-0002 feature 2.1 is aspirational; the actual final count may be 10–14 depending on how categories consolidate. Not a scope change.

---

## Rationale

### Why four views instead of one dashboard

Considered a single-window dashboard with everything visible (calendar + navigation + chart + learning content simultaneously). Rejected because:

- Too much on screen at once for a personal tool where users focus on one thing at a time (per ADR-0001 "explorer feel, not dashboard")
- Charts benefit from full content area width — cramming them into a corner loses value
- Sidebar-as-contextual-content already gives navigation without dedicating persistent screen space

The four-view model matches the actual use cases (UC-1 through UC-5 from `use-cases.md`): calendar-first check-in, category browsing, data lookup, correlation exploration, learning. Each use case has a natural primary view.

### Why menu bar is heavy

A common temptation is to hide most functionality in the menu bar and keep the UI minimal. This app leans into the menu bar because:

1. **Mac users expect it.** Native menu bar is table-stakes UX on macOS.
2. **Cross-platform for free.** `QMenuBar` maps to Mac top-bar and Win/Linux in-window with no code changes.
3. **Global actions belong there, not in the UI.** Refresh all data, open preferences, quit — these are app-level, not view-level.
4. **Keyboard shortcuts feel first-class.** ⌘1-4 for view switching is more discoverable via menu bar than a hidden shortcut.

### Why sidebar is contextual, not universal

A universal sidebar (same content on every view) is simpler to build but redundant. On the Calendar, category filters make sense; on Series Detail, they don't. On Explorer, the nav tree makes sense; on Calendar, it's just clutter that competes with the filters.

Contextual sidebar adds ~2-3 QWidget states worth of code but gives every view the right nav for its purpose.

### Why Push (reflow), not overlay

Charts are the primary content and benefit from full width. Overlay sidebar covers the very content the user wants to see. Push reflow means chart gets full width when sidebar is closed. Divider drag lets users tune the split per session.

Downside: chart re-flows on toggle. Modest visual jarring, offset by the value of full-width charts.

### Why Focus Mode

Small feature, low cost. Users occasionally want to just stare at a chart without app chrome around it. Also serves accidental use cases (screen sharing, presentations, deep concentration). Not core, but the effort-to-value ratio is favorable.

### Why single-page Series Detail instead of tabs

Considered Chart | Learning | Data tabs. Rejected because:

1. A personal tool where the user *wants* to build understanding shouldn't hide learning content behind a tab. Making it scroll-below-chart puts it in the natural reading path.
2. Tabs suggest independent contexts. Chart + explanation + market impact aren't independent — they're one unit of "understanding this indicator."
3. Simpler build.

If the Series Detail page becomes unwieldy after real content is added (each series has multi-paragraph explanations), we can revisit. First-pass: single scroll.

---

## Consequences

### Positive

- **Clear structural boundaries.** Every UI question ("where should X live?") has a defensible answer based on this ADR.
- **Contextual sidebar means less mental switching.** The nav on screen matches what the user is doing.
- **Menu bar handles global commands cleanly.** UI stays uncluttered.
- **Focus Mode gives a "just the chart" option** without complicating the default view.
- **Four views maps to five use cases naturally.** No use case is starved for a home.

### Trade-offs Accepted

- **Contextual sidebar is more code than universal.** Justified by UX gain.
- **Push reflow reflows the chart.** Minor visual cost accepted for full-width chart benefit.
- **No breadcrumbs.** Relies on sidebar tree for hierarchy awareness. Acceptable for v1; reconsider if users get lost.
- **No rail mode in v1.** Sidebar is binary (open/closed). Rail mode considered but deferred.
- **No dashboard view.** Considered but rejected as contrary to the explorer feel (ADR-0001).
- **Preferences is modal, not a view.** Fine for OS conventions; may feel slightly heavier than an inline settings page. Standard trade-off.

### Consequences for the Build

The following components will need to exist (naming approximate; actual class names emerge during implementation):

- `MainWindow` — the shell containing menu bar + sidebar + content area
- `Sidebar` — contextual container that swaps content based on active view
- `CalendarView` — embedded `QWebEngineView`
- `ExplorerView` — category card grid and release/series lists
- `SeriesDetailView` — the chart page (chart + controls + learning content)
- `CoreIndicatorsView` — Baumohl top-10 cards
- `PreferencesDialog` — modal with tabs
- `SidebarContext<View>` — one per view (CalendarFilters, NavTree, CoreIndicatorFilters)
- `FocusModeManager` — coordinates hiding/showing chrome
- `SettingsStore` — reads/writes persisted UI state

Naming is a v1 concern; this is scaffolding to make the ADR concrete.

### Consequences for Users (well, You)

- **Default landing view is Calendar.** Per ADR-0001 and confirmed here.
- **⌘1-4 always jumps between views** regardless of current context.
- **⌘\\ toggles sidebar** in any view.
- **⌘⇧F enters/exits Focus Mode.** Not core; won't be missed if unused.
- **⌘, opens Preferences.** Standard OS shortcut.
- **UI state remembered across sessions.** Reopens the way you closed it.

---

## Alternatives Considered

### Alternative 1: Single-window dashboard

Everything visible simultaneously — calendar sidebar, category tree, chart, learning content, all on one screen at once.

**Rejected**: too dense for a personal tool where you focus on one thing at a time. Charts get squeezed. Learning content becomes a wall of text.

### Alternative 2: Tabbed interface (browser-style)

Each view is a tab; user opens multiple series-detail tabs and switches between them.

**Rejected**: adds tab management UI, tab-close discipline, and confusion about which tab is "current." Overkill for a personal tool. Menu-bar-based view switching (⌘1-4) covers the same need with less chrome.

### Alternative 3: Overlay sidebar (like a slide-out drawer)

Sidebar floats over content instead of pushing it.

**Rejected**: covers the chart you're trying to read. Push reflow gives full-width charts when sidebar is closed, which is the more valuable state.

### Alternative 4: Series Detail as multi-tab (Chart | Learning | Data | History)

Each aspect of a series gets its own tab within the Series Detail view.

**Rejected**: hides learning content behind a click, contradicting ADR-0001's learning-first objective. Single scrolling page is simpler and puts context in the natural reading path.

### Alternative 5: Right sidebar for context, left sidebar for navigation

Two persistent sidebars: left is nav, right is context (metadata, learning content).

**Rejected**: over-engineered for v1. Chart page becomes cramped between two sidebars. Wastes space.

### Alternative 6: No sidebar; full-screen views with modal navigation

Each view is full-screen; navigation happens via menu bar and command palette (⌘K style).

**Rejected**: command palettes are power-user patterns and require training. Sidebar tree is a more familiar affordance for browsing hierarchical content (Category → Release → Series).

---

## Open Questions (Deferred)

- **Command palette (⌘K)** — worth adding in v1.1? Fast series search across all catalog data. Currently deferred; the Explorer sidebar + flat search cover the same need with more mouse work.
- **Multiple monitors** — should the app support "chart on second monitor" pattern via detachable window? Deferred; power feature.
- **Recent history** (feature 2.6, Could) — where does it live in the sidebar? Bottom of Explorer sidebar with disclosure toggle? Deferred.
- **Compare mode UX details** — when Compare is active, do the two series share date range and transform controls, or have independent ones? Design detail for the implementation phase.
- **Category taxonomy** — final list of categories for the sidebar tree. Depends on catalog work. Not blocking this ADR.

---

## Approval

- [ ] Four primary views + Preferences dialog structure accepted
- [ ] Menu bar as heavy actor accepted
- [ ] Push (reflow) sidebar with contextual content accepted
- [ ] Focus Mode as v1 feature accepted
- [ ] No breadcrumbs, no dashboard, no tabs for Series Detail — all accepted
- [ ] Ready to proceed to implementation planning

*Confirm in conversation to move from Proposed to Accepted.*
