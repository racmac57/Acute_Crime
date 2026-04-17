# Command Staff Email Body — Persistent Hotspots

## Subject Line Options
- T4 Persistent Hotspots: Targeted Patrol Allocation (2024-2026 Baseline)
- Immediate Patrol Targeting: Top Persistent Group/Fight Hotspots (Citywide)
- Operational Brief: Historical Risk Patterning for Directed Patrol Deployment

## Email Body (Paste-Ready)

Command Staff,

Attached is the T4 persistent hotspot package built from 2024-01-01 through 2026-03-31 to support targeted patrol allocation for group/fight-related activity. This is historical risk patterning (where incidents repeatedly concentrate by location and time), not predictive policing. The top locations show sustained activity across many active months and consistent day/time concentration suitable for directed patrol scheduling.

- **0 Block Newman St** — 297 incidents, high confidence; strongest window: **Thu/Fri, 20:00-23:00**, late month.
- **200 Block Essex St** — 248 incidents, high confidence; strongest window: **Thu/Fri, 16:00-19:00**, early month.
- **100 Block Hudson St** — 163 incidents, high confidence; strongest window: **Mon/Wed, 12:00-15:00**, late month.

- **Caveat:** `trend_90d=down` is a seasonal/context artifact for this anchor date and should not be interpreted as automatic hotspot resolution.
- **Caveat:** spatial overlays (`Post`, `PDZone`, `Grid`, lat/lon) are deferred; ArcGIS overlay is still required before final field deployment tuning.

- **Requested command action:** Approve targeted patrol deployment windows for the top locations and authorize the ArcGIS overlay follow-up to finalize post/zone assignment.

## Attachments
- `Docs/deliverables/T4_persistent_hotspots_citywide.csv`
- `Docs/deliverables/T4_persistent_hotspots_command_staff.md`
- `Docs/deliverables/T4_persistent_hotspots_technical_appendix.md`

# Command Staff Email — Persistent Hotspots Release (2026-04-17)

**Classification:** Law Enforcement Sensitive — location/condition-based; no individual targeting.

## Subject Line Options

1. T4 Persistent Hotspots — Top 10 Citywide, Targeted Patrol Windows Ready for Review
2. Persistent Hotspot Release (2024-01 through 2026-03) — Command Decision Requested
3. Historical Risk Patterning — Top 10 Deployment Locations + Time Windows

## Body

Team,

The T4 persistent hotspot package for horizon 2024-01-01 through 2026-03-31 is complete and posted under `Docs/deliverables/`. This is historical risk patterning (frequency + persistence + recency + severity on filtered CAD and RMS Part 1 violent data, DV-excluded) intended to support targeted patrol allocation — where and when. It is advisory; field supervisors ground-truth before deployment.

**Top deployment locations + best windows (high confidence):**

- **0 Block Newman St** — Thu/Fri, Night 20-23, late-month (21-31). Risk 0.91, 297 incidents over 19 active months.
- **200 Block Essex St** — Thu/Fri, Evening Peak 16-19, early-month (1-10). Risk 0.80, 248 incidents over 21 active months.
- **100 Block Hudson St** — Mon/Wed, Afternoon 12-15, late-month (21-31). Risk 0.74, 163 incidents over 27 active months.

**Caveats (read before briefing down):**

- `trend_90d = down` on most top-10 rows is largely a **seasonal artifact** (Jan-Mar 2026 vs Oct-Dec 2025 street-disorder baseline). Do **not** treat it as hotspot resolution. Sustained multi-cycle decline is the signal; one cycle is not.
- **Spatial enrichment is deferred.** Post, PDZone, Grid, and lat/long are not joined to these rows yet. Overlay against the ArcGIS Pro T4 map before finalizing post-level tasking.

**Requested decision:** Approve the top-10 list as the basis for the next-cycle targeted patrol plan, and authorize the ArcGIS overlay follow-up to assign each hotspot to its post/zone for final deployment tasking.

Full package: `Docs/deliverables/T4_persistent_hotspots_command_staff.md`, citywide CSV, and method appendix. Happy to walk through in person.

— R. A. Carucci #261, SSOCC
