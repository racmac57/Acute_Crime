# Release Note — Persistent Hotspots MVP+

**Commit:** `f24b18abb4c5bd0c0592e04bc1c95042037e02d3` (short `f24b18a`)
**Branch:** `main`
**Remote:** `origin/main` (https://github.com/racmac57/Acute_Crime)
**Published:** 2026-04-17T04:01:31-04:00 (commit timestamp)
**Classification:** Law Enforcement Sensitive — location-based, condition-focused, no individual targeting.

## What shipped

- Strategic persistent-hotspot patrol product for group/fight-relevant incidents over 2024-01-01 → 2026-03-31, scored across 743 locations from 4,772 kept CAD events + 835 kept RMS events (post two-layer DV exclusion).
- Top-10 hotspots CSV (23-column schema) plus a command one-pager and a one-page method/caveats note — all three in `Docs/deliverables/`, reproducible via `python -m Scripts.t4.persistent_hotspots`.
- Composite score tilts toward persistence + severity (0.20 freq / 0.30 persistence / 0.20 recency / 0.30 severity) with recency decay, so sustained serious activity outranks short low-severity bursts.

## Known caveats

- `trend_90d = down` on most top-10 rows at the 2026-03-31 anchor is a winter/fall seasonality artifact, not hotspot resolution — require ≥2 consecutive cycles of decline before concluding a trend.
- Spatial enrichment (lat/long, Post, PDZone, Grid) deferred on the top-10 CSV; use the ArcGIS Pro T4 map for post/zone overlays before deployment.
- Confidence is a qualitative gate (high/medium/low by volume + persistence), not a calibrated probability; treat low-band rows as analyst-only, never as briefed hotspots.

## Next iteration

- Calibrate confidence against outcome data (next-cycle recurrence or CPTED/complaint-resolution follow-up) to move from gate to probability.
- Publish ArcGIS hosted feature layer `T4_Persistent_Hotspots_2024_2026_Q1` with Post/PDZone/Grid joined, wired into the T4 Dashboard web map.
- Normalize `trend_90d` to YoY (same-quarter prior year) to eliminate the seasonal artifact once each location has ≥2 full years of data.

## Deliverable paths

- CSV (top 10): `Docs/deliverables/T4_persistent_hotspots_citywide.csv`
- Command one-pager: `Docs/deliverables/T4_persistent_hotspots_command_staff.md`
- Method/caveats note: `Docs/deliverables/T4_persistent_hotspots_technical_appendix.md`
- Handoff: `Docs/handoffs/handoff_20260417_persistent_hotspots_mvp_plus.md`
- Pipeline: `Scripts/t4/persistent_hotspots.py`
