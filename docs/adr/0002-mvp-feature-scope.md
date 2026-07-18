# ADR-0002: MVP Feature Scope

**Status**: Proposed
**Date**: 2026-07-18
**Deciders**: Carey Carroll
**Supersedes**: None
**Related**: ADR-0001 (Vision & Scope), `docs/specs/use-cases.md`, `docs/specs/feature-inventory.md`

---

## Context

ADR-0001 established the vision and scope. `feature-inventory.md` enumerated ~103 candidate features across 10 sections. `use-cases.md` defined 5 concrete usage scenarios (UC-1 through UC-5).

This ADR formalizes the MoSCoW prioritization pass applied to the feature inventory and locks the v1 feature set. It is the answer to "what are we building first?"

Without this ADR, every downstream design and engineering decision becomes an open question. Locking scope here makes the next phases (Information Architecture, Wireframes, Technical Design) tractable.

---

## Decision

### MoSCoW Distribution

| Priority | Count | % of Total |
|---|---:|---:|
| **Must (M)** — required for v1 | 36 | 35% |
| **Should (S)** — post-v1 top priority | 34 | 33% |
| **Could (C)** — nice-to-have | 22 | 21% |
| **Won't (W)** — explicitly deferred | 12 | 12% |
| **Total** | 104 | 100% |

The authoritative source is `docs/specs/feature-inventory.md`. This ADR summarizes the decision; the inventory carries the row-level detail.

### v1 Musts (What Ships)

The following 36 features constitute v1. Each is required for at least one of UC-1 through UC-5 to work at all.

#### Calendar (1 feature)
- **1.1** Embed Investing.com calendar widget in `QWebEngineView`

#### Category & Series Navigation (4 features)
- **2.1** Sidebar with top-level categories
- **2.2** Expand category → releases
- **2.3** Expand release → series
- **2.4** Flat search across all series by name or ID

#### Chart Viewing (8 features)
- **3.1** Single-series line chart via PyQtGraph
- **3.2** Interactive pan and zoom
- **3.3** Crosshair with tooltip
- **3.4** Date range picker (1Y / 5Y / 10Y / MAX / custom)
- **3.5** Transform selector (Level / YoY % / MoM % / QoQ % / Annualized)
- **3.9** Chart title, subtitle, axis labels auto-populated from catalog
- **3.10** Attribution/source line
- **3.11** Last-updated timestamp on chart

#### Correlation & Comparison (4 features)
- **4.1** "+ Compare" button
- **4.2** Same-unit overlay
- **4.9** Cap on overlay count (3–4 max)
- **4.10** Legend with color, name, current value

#### Market Impact & Core Indicator Metadata (3 features)
- **5.1** Tag series with market impact (Stocks / Bonds / Dollar / All / None)
- **5.5** Display market impact on chart page
- **5.6** "Core Indicators" curated view (Baumohl's top-10 lists)

#### Learning Content (4 features)
- **6.1** Three-tier explanations (sentence / paragraph / detailed)
- **6.3** "What it measures" section
- **6.5** "Why it matters" section
- **6.9** Release schedule info

#### Data Management (5 features)
- **7.1** FRED API client with key from `.env`
- **7.2** Local SQLite cache
- **7.4** Manual refresh button per series
- **7.7** "Last synced" timestamp
- **7.9** Handle FRED rate limits gracefully

#### Configuration (1 feature)
- **8.1** FRED API key management via `.env`

#### UI Framework (5 features)
- **9.1** Native PySide6 window with menu bar
- **9.2** Resizable panes (sidebar + main content)
- **9.5** Cross-platform (macOS, Windows, Linux)
- **9.9** Loading indicators
- **9.10** Error/toast notifications

#### Distribution (1 feature)
- **10.1** Run from source (`python app.py`)

### Notable Won'ts (Explicitly Deferred to v2+)

These are the 12 features cut for v1. Listing them here makes the deferral deliberate rather than accidental.

| # | Feature | Why Deferred |
|---|---|---|
| 1.6 | Build our own calendar UI | Investing.com widget satisfies UC-1 with far less effort |
| 2.7 | Filter categories by user relevance | Curation problem; solve after learning what user hides |
| 2.8 | Custom user-defined categories | Personalization can wait until app is used regularly |
| 4.8 | Lead/lag adjustment control | Statistical feature; not needed for basic UC-4 |
| 6.13 | Inline term tooltips | Requires glossary + hover UI; complex for marginal gain |
| 7.11 | Data revision tracking (vintages) | FRED handles this on its site; personal tool doesn't need it |
| 8.8 | Auto-launch on system startup | Personal preference the user can set via OS |
| 9.8 | Splash screen | Aesthetic only; not needed for personal tool |
| 10.5 | Signed macOS build | Only matters when distributing to others (ADR-0001 non-goal) |
| 10.6 | Auto-update mechanism | Only matters when distributing to others |
| 10.7 | Crash reporting | Only matters when distributing to others |

The remaining "not-in-v1" features (34 Should + 22 Could) are parked, not rejected. They are candidates for v1.1, v1.2, etc.

---

## Rationale

### Why 36 Musts and not fewer

The Musts cluster into three roughly-equal groups:

1. **The chart experience** (sections 3 + 4): 12 features. If charts don't work well, the app fails UC-2, UC-3, UC-4, UC-5.
2. **The plumbing** (sections 1, 2, 7, 8): 11 features. Calendar, navigation, data pipeline, config. Without these there is no app.
3. **The differentiators** (sections 5, 6): 7 features. Market impact tagging and learning content are what make this tool distinctive per ADR-0001's "learning" objective.
4. **The frame** (sections 9, 10): 6 features. Basic native app shell.

Cutting further would drop below viable. The threshold for "personal tool worth using weekly" (ADR-0001 success criterion) requires all four groups.

### Why some seemingly-obvious features are Should, not Must

- **Recession shading (3.7)** — Adds real interpretive value but is not required for a chart to be useful. Prioritized as first-shipped Should.
- **Data export (3.13, 3.14)** — Users can screenshot or query FRED directly for CSVs. Nice, not blocking.
- **Favorites (2.5)** — Requires state management, list UI, and pin/unpin flows. Meaningful lift for a v1 that already has many chart controls.
- **Recession shading, dual-axis (4.4), scatter mode (4.5)** — Powerful correlation modes but same-unit overlay (4.2) already satisfies UC-4 at a basic level.
- **Offline mode (7.10)** — SQLite cache exists in Must; graceful offline handling requires additional connectivity detection and UX. Ships second.

### Why some tempting features are Could or Won't

- **Progressive disclosure of learning tiers (6.2)** — Interesting UX but not essential; user can just see all three tiers stacked. Marked Should to prompt post-v1 refinement.
- **Auto-scheduled data refresh (7.6)** — Manual refresh (Must) covers UC-2 and UC-5 adequately. Automation is convenience, not capability.
- **Dark mode (9.6)** — Genuinely popular but pure aesthetic. Ships when core is stable.
- **PyInstaller bundles (10.2–10.4)** — Nice for double-click launch but personal user is comfortable with terminal. Ships when packaging is stable.

### Alignment with Use Cases

Each Must maps to at least one use case:

| Use Case | Primary Musts |
|---|---|
| **UC-1 Morning Check-In** | 1.1, 9.1, 9.5 |
| **UC-2 Post-Release Lookup** | 2.1–2.4, 3.1–3.11, 7.1–7.9 |
| **UC-3 Learning Session** | 5.1, 5.5, 5.6, 6.1, 6.3, 6.5, 6.9 |
| **UC-4 Correlation Exploration** | 4.1, 4.2, 4.9, 4.10 |
| **UC-5 Anticipating a Major Release** | 1.1, 3.x, 5.5, 6.9 |

No Must is orphaned. No use case is missing critical Musts.

---

## Consequences

### Positive

- **Scope is finite and defensible.** Every subsequent design decision has a reference: "does this serve a Must?"
- **Cutting is now easy.** New feature ideas hit the inventory; they get an S/C/W by default, not an M. Musts require a change to this ADR.
- **The three-way scope (Must / v1 / not v1) becomes a shared vocabulary.** Ambiguity about "is this in scope" is eliminated.
- **Post-v1 roadmap has candidates already.** The 34 Shoulds are the natural v1.1/v1.2 backlog, pre-sorted.

### Tradeoffs Accepted

- **v1 will feel spare in places.** No favorites, no dark mode, no exports. Users who expect polish out of the gate will notice.
- **Learning content is expensive to produce.** The Musts include four learning fields per series. At ~50 series, that's ~200 content items to author. Estimated effort not trivial.
- **Calendar → chart deep-linking is a Should, not Must.** Users will need to manually navigate from a calendar release to the matching chart in v1. Friction on the UC-1 → UC-2 workflow.
- **No data export in v1.** If the user wants to analyze data outside the app, they use FRED directly. Acceptable given ADR-0001 non-goals.

### Effort Implications

Rough scoping (order of magnitude, not commitment):

| Category | Estimated Effort |
|---|---|
| **PySide6 shell + navigation** (1.1, 2.x, 9.x) | 1 weekend |
| **FRED integration + cache** (7.x, 8.1) | 1 weekend |
| **Chart view with transforms** (3.x) | 2 weekends |
| **Overlay/compare** (4.x) | 1 weekend |
| **Catalog schema + market impact + learning content** (5.x, 6.x, 10.1) | 2–3 weekends + ongoing content authoring |
| **Polish + fixes** | 1–2 weekends |

Total: ~8–10 weekends of active build, plus ongoing catalog content work. AI-assisted coding compresses this meaningfully.

---

## Follow-on Releases (Not Binding)

These sketches are illustrative, not commitments. They help think about how Shoulds are ordered post-v1.

**v1.1 — Comfort & Comparison**
- 2.5 Favorites
- 3.7 Recession shading
- 3.13 / 3.14 Chart & data export
- 4.3 Rebased-to-100
- 5.3 Leading indicator flag
- 7.10 Offline mode

**v1.2 — Analytical Depth**
- 4.4 Dual y-axis
- 4.5 Scatter + correlation coefficient
- 4.7 Spread mode
- 5.4 Filter by market impact
- 6.2 Progressive disclosure

**v1.3 — Convenience & Packaging**
- 7.6 Scheduled refresh
- 8.2 Keyring for API key
- 8.3 Preferences UI
- 9.3 Window state persistence
- 9.4 Keyboard shortcuts
- 10.2 / 10.3 / 10.4 PyInstaller bundles

**v2 territory (per Won'ts):** international data, multi-user, auto-update, crash reporting.

---

## Alternatives Considered

**Broader v1 (60+ features)**
Rejected. Musts already push v1 to the edge of "personal weekend project." Adding 30+ more would extend to months and risk the classic never-finish trap.

**Narrower v1 (~20 features)**
Considered. Cutting to just the calendar + a bare chart view would ship faster but fail UC-3 (learning) and UC-4 (correlation). The distinctive value in ADR-0001 disappears. Rejected.

**Different prioritization framework (Kano, RICE)**
Considered. MoSCoW is best-fit for a personal project where cost and reach aren't meaningful axes. Kept.

**Per-section shipping (release sections independently)**
Considered. Would technically be possible — ship calendar + navigation first, then charts, then learning. Rejected as awkward for the user; incomplete v1 feels worse than a longer wait for a whole one.

---

## Open Questions (Deferred to Later ADRs)

- **How does the user find a series if they don't know the name?** Sidebar + search covers most cases, but "browse Core Indicators" is a distinct entry point. ADR-0003 (IA) will decide the top-level nav.
- **What's the exact taxonomy for the catalog?** 12 categories, N releases per category, N series per release. Details of the tree are IA work.
- **Where does the learning content live?** JSON alongside the catalog, or markdown files, or database. Technical design.
- **What's the app called?** Still deferred. Placeholder: "the App."
- **What's the release cadence for post-v1?** Not decided. Might be "when I feel like it."

---

## Approval

- [ ] Musts list accepted as written
- [ ] Won'ts list accepted as deferrals
- [ ] Follow-on release sketches acknowledged as non-binding
- [ ] Ready to proceed to ADR-0003 (Information Architecture)

*Once confirmed, this ADR moves from Proposed to Accepted and v1 scope is locked.*
