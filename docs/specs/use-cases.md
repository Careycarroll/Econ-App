# Use Cases

**Status**: Draft — for review alongside ADR-0001 and feature-inventory.md
**Related**: ADR-0001 (Vision & Scope), feature-inventory.md, forthcoming ADR-0002 (MVP Feature Scope)

---

## Purpose

Concrete scenarios of how the app will actually be used. These are the yardstick every feature must earn its place against: if a proposed feature doesn't serve one of these use cases, it's a candidate for cutting.

Each scenario describes:
- **Context** — the situation the user is in before opening the app
- **Goal** — what they want to accomplish
- **Flow** — the steps they'd take
- **Success** — what "done" looks like
- **Frequency** — how often this happens

---

## UC-1: Morning Check-In

**Context**: Weekday morning. User is about to start the day and wants to know what economic releases are coming.

**Goal**: See today's and this week's releases at a glance.

**Flow**:
1. Open the app.
2. App opens directly to the calendar view (per ADR-0001).
3. User scans today's releases: what's coming, at what time, at what importance.
4. Optionally glances at the rest of the week for anticipation.
5. Closes app or moves to a specific chart if a release catches their attention.

**Success**: User knows within 30 seconds what's being released today.

**Frequency**: Daily, or at least on days with expected releases (CPI Tuesdays, jobs Fridays, FOMC weeks).

---

## UC-2: Post-Release Lookup

**Context**: A release just came out. User heard about it on news/podcast/Twitter or via the calendar. They want to see the actual number in context.

**Goal**: View the released data in a chart, understand how it compares to recent history.

**Flow**:
1. Open app (or already open).
2. Navigate to the relevant series — either via the calendar (click the release) or via category navigation (Prices → CPI).
3. See the chart with the new data point.
4. Toggle transforms if needed (level / YoY % / MoM %).
5. Optionally read the "why this matters" learning content to reinforce interpretation.

**Success**: User can find and view any tracked series in under 15 seconds (per ADR-0001 success criteria).

**Frequency**: 2–5x per week during active release periods; less during quiet weeks.

---

## UC-3: Learning Session

**Context**: User is reading a news article, listening to a podcast, or curious about something they encountered. Doesn't fully understand a concept (e.g., "core PCE," "Sahm Rule," "yield curve inversion").

**Goal**: Build understanding of what an indicator measures, why it matters, and how it behaves.

**Flow**:
1. Open app.
2. Navigate to the relevant series via category or search.
3. Read the multi-tier learning content:
   - One-sentence definition
   - One-paragraph overview
   - Detailed breakdown with methodology, market impact, related series, pitfalls
4. Explore related series linked from the current one.
5. Optionally chart historical behavior to see patterns.

**Success**: User leaves with a stronger grasp of an indicator than when they opened the app.

**Frequency**: 1–3x per week, more during first months of app use, tapering as familiarity grows.

---

## UC-4: Correlation Exploration

**Context**: User has a hypothesis — "does yield curve inversion predict recessions?" or "how does CPI relate to Fed Funds Rate?" — and wants to visualize it.

**Goal**: Overlay two series and see how they move relative to one another.

**Flow**:
1. Open app.
2. Navigate to primary series (e.g., 10Y-2Y spread).
3. Add a comparison series via "+ Compare" (e.g., NBER recession indicator, unemployment rate).
4. Toggle visualization mode: dual-axis, rebased-to-100, or scatter with correlation coefficient.
5. Adjust date range to focus on a specific era.
6. Interpret the relationship.

**Success**: User can visualize a correlation hypothesis in under a minute and form a personal view of the relationship.

**Frequency**: Weekly or biweekly. Higher during active research phases.

---

## UC-5: Anticipating a Major Release

**Context**: CPI or jobs report drops tomorrow morning. User wants to prepare by refreshing their understanding of the last few prints, what analysts expect, and how markets typically react.

**Goal**: Build context for an upcoming release so they can interpret it quickly when it comes out.

**Flow**:
1. Open app.
2. Calendar shows the upcoming release with time and importance.
3. Click the release → jumps to the associated chart(s).
4. Review the last 12–24 months of prints.
5. Read the market impact tags (e.g., "high impact on stocks, bonds, and dollar").
6. Optionally add a related series for context (CPI + Core CPI overlay).
7. Close app, prepared for tomorrow.

**Success**: User feels prepared to interpret the release when it happens.

**Frequency**: A few times per month, aligned with high-impact release schedule.

---

## Non-Use-Cases (Explicitly Not Supported)

To clarify scope by contrast, these are things the app is **not** for:

- **Real-time trading decisions** — the app is not a trading terminal. No live prices, no order entry, no intraday tick data.
- **Sharing analyses with others** — no export-to-share, no collaborative annotations, no publishing.
- **Multi-user access** — one user, one machine.
- **Forecasting or modeling** — the app displays data; it doesn't predict.
- **Data extraction from PDF reports** — reports are for reading, not parsing.
- **Deep sector or company-level analysis** — the app is about macro indicators, not stock picking.

---

## How These Feed ADR-0002

During MoSCoW prioritization, each feature in `feature-inventory.md` will be evaluated against these use cases:

- **Must**: Feature is required for one of UC-1 through UC-5 to work at all.
- **Should**: Feature meaningfully improves one of UC-1 through UC-5.
- **Could**: Feature adds polish or enables edge cases within these use cases.
- **Won't (v1)**: Feature doesn't serve any of these use cases, or serves them so marginally that it's not worth the build cost.

If a feature seems important but doesn't map to any use case, that's a signal that either:
- The use cases are incomplete (add a new one)
- The feature is out of scope (cut it)
