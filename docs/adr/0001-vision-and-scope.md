# ADR-0001: Vision & Scope

**Status**: Proposed
**Date**: 2026-07-10
**Deciders**: Carey Carroll
**Supersedes**: None

---

## Context

We are beginning the design of a personal desktop application for exploring U.S. economic data. Prior conversation has established a working direction (Python + PySide6 + PyQtGraph, FRED as data backbone, embedded calendar widget, curated catalog of series). Before making detailed design decisions — page layouts, feature specifications, UI patterns, chart behaviors — we need to lock in a clear vision statement that serves as the reference point for all subsequent decisions.

Without a locked vision, every downstream decision becomes an open question and every new feature idea threatens to redirect the project. This ADR establishes the boundaries.

---

## Decision

### Vision Statement

**A personal desktop application for exploring and learning about U.S. economic data. The app pairs the daily economic release calendar with an interactive chart explorer backed by FRED, helping the user understand what data is being released and build fluency with U.S. macroeconomic indicators through browsable, curated exploration.**

### Target User

**A single user**: a quantitatively-inclined observer of the U.S. economy who wants a personal tool for learning and lookup — not a professional trading terminal, not a shared product, not a research platform.

### Core Value Propositions

1. **Awareness** — surface upcoming economic releases so the user knows what's coming and when.
2. **Exploration** — provide fast, interactive access to any curated FRED series with meaningful transforms and comparisons.
3. **Learning** — embed context and explanation alongside data so that browsing builds understanding over time.

### Primary Interaction Modes

- **Calendar-first landing** — the app opens on the release calendar so the user sees what's happening today/this week.
- **Explorer navigation** — deep dive into any series via curated category navigation.
- **Contextual learning** — every series carries explanation at multiple levels of depth.

---

## Rationale

- **Personal-use scope** keeps design honest. No hypothetical users, no feature bloat justified by "someone might want this."
- **FRED-first data strategy** builds on the earlier decision that FRED covers ~90% of U.S. macro data needs with minimal integration burden.
- **U.S.-only focus** reflects the user's actual stated interests and defers international complexity indefinitely.
- **Calendar + Explorer pairing** captures the two natural modes of engaging with economic data: temporal awareness (what's coming?) and on-demand lookup (show me CPI history).
- **Learning as a stated objective** distinguishes this from a pure data tool — it means we invest in explanatory content, curated catalogs, and progressive disclosure of complexity.
- **Desktop application** (vs. web) reflects the user's preference for a contained, native-feeling tool that works offline and downloads data locally.

---

## Non-Goals

The following are explicitly out of scope and should not be revisited without a new ADR:

- **Not a commercial or multi-user product.** No authentication, no accounts, no sharing, no billing.
- **Not a professional trading platform.** No real-time market data, no order entry, no derivatives modeling.
- **Not competing with Bloomberg, Haver, Trading Economics, Refinitiv, or similar.** We're not rebuilding what already exists.
- **Not attempting international coverage in v1.** U.S. data only. International data is a possible v2+ direction but a redesign concern.
- **Not parsing PDF reports into structured data.** Reports are for reading (via links to source), not for data extraction.
- **Not rebuilding the economic calendar itself.** The calendar is embedded from an existing provider (Investing.com) until such time as we have reason to build our own.
- **Not a general-purpose data tool.** Focus is macroeconomic time series, not company financials, not commodities detail, not micro-data.

---

## Success Criteria

The vision is being served if, after the app is built:

1. **Habitual usage** — the user opens the app at least weekly.
2. **Speed of lookup** — the user can find any series in their curated catalog and view a chart in under 15 seconds.
3. **Learning effect** — the user can point to concepts or series they now understand that they didn't before building the tool.
4. **Reliability** — the app runs consistently on the user's primary machine (Windows/Mac/Linux, per user's cross-platform requirement).
5. **Personal fit** — the user prefers this tool over alternatives (FRED website, Trading Economics, etc.) for their specific workflow.

Failure modes to watch for:

- The app becomes something the user "should" use but doesn't
- Feature creep causes the app to feel bloated relative to its personal-use scope
- The learning content is ignored in favor of raw data lookup (or vice versa) — signals a mismatch with actual usage

---

## Consequences

### Positive

- Clear scope enables clear "no" answers to feature suggestions
- U.S.-only means we can defer significant complexity (SDMX, foreign currency handling, cross-country comparisons)
- Personal-use scope eliminates auth, permissions, multi-tenancy, support tooling
- FRED-first minimizes API integration burden (one API covers most needs)
- Learning focus differentiates the tool from generic data viewers

### Tradeoffs Accepted

- **Not shareable** — the tool cannot be handed to another user without meaningful additional work (packaging, distribution, docs).
- **Calendar dependency** — using an embedded third-party calendar (Investing.com) creates a soft dependency on their service. If they change their embed policy, we have a problem.
- **Learning content is ongoing work** — the value of the tool depends on curated context, which is content work, not just code work.
- **U.S.-only ceiling** — if the user's interests expand to international data, this design won't accommodate it gracefully.
- **Desktop-only** — no browser access from other devices. The user has explicitly accepted this tradeoff.

---

## Alternatives Considered

**Multi-user web app**
Rejected: scope creep. Would require auth, hosting, support, and design compromises for imaginary users.

**Full FRED replacement / data platform**
Rejected: FRED already exists and is excellent. Rebuilding it wastes effort and produces an inferior copy.

**Calendar-only app**
Rejected: Trading Economics and Investing.com already do this well. No differentiation.

**Chart-only app with no calendar**
Rejected: calendar is core to the user's stated interest ("I want to see when reports release"). Removing it removes primary value.

**Data-only tool without learning content**
Rejected: learning is a stated primary objective. Ignoring it produces a tool the user has less use for.

**International/global scope from day one**
Rejected: significant complexity increase. Defer to future ADR if/when needed.

---

## Open Questions (Deferred to Later ADRs)

- **Naming** — the app currently has no name. Placeholder: "the App." A separate ADR (or informal decision) will settle this.
- **Distribution strategy** — for now, run from source. Packaged executables (via PyInstaller or similar) deferred.
- **Data storage schema** — SQLite decided at high level; schema design deferred to technical ADRs.
- **Update / refresh cadence** — how often the app checks FRED for new data. Deferred to technical design.

---

## Approval

- [ ] Vision statement accepted as written
- [ ] Non-goals accepted
- [ ] Success criteria accepted
- [ ] Ready to proceed to ADR-0002 (MVP Feature Scope)

*Sign here (metaphorically) by confirming in conversation, then this ADR moves from "Proposed" to "Accepted."*
