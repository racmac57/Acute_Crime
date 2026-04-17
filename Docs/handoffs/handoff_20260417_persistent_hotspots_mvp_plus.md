# Handoff — 2026-04-17 — Persistent Hotspots MVP+

**Status:** Shipped. Approved for briefing.
**Operator:** R. A. Carucci #261 (SSOCC / HPD)
**Classification:** Law Enforcement Sensitive. Location-based, condition-focused. No individual targeting.

---

## Scope

Strategic persistent-hotspot patrol product for group/fight-relevant incidents.
Historical risk patterning — NOT deterministic prediction.

- **Horizon:** 2024-01-01 → 2026-03-31 (2.25 years)
- **Analysis anchor (recency decay):** 2026-03-31
- **Sources:** CAD yearly + monthly (2024, 2025, 2026_01..03) and RMS yearly + monthly (same span)
- **DV blocklist:** `Data/dv_case_numbers_for_t4.csv` (1,536 cases; source_date_end max 2026-04-16)
- **Ethical basis:** U.S. Const. 4th/14th; NJ AG Directives 2021-6 and 2023-1; HPD Department Policy

## Filtering outcome

| Source | Raw in horizon | Kept after filters |
|---|---:|---:|
| CAD | 191,195 | **4,772** (group/fight-relevant, citizen-generated, disp not Unfounded/Canceled/Checked OK) |
| RMS | 51,854 | **835** (NIBRS Part 1 / violent, post two-layer DV exclusion) |
| DV excluded (case-number blocklist / Layer 1) | — | 981 |
| DV excluded (type fallback / Layer 2) | — | 1,025 |
| Distinct location keys scored | — | **743** |
| Top 10 delivered to command | — | **10** |

## Top 5 persistent hotspots (for the verbal brief)

| # | Location | Risk | n | Months | Window | Trend 90d | Confidence |
|---|---|---:|---:|---:|---|---|---|
| 1 | 0 Block Newman St | 0.908 | 297 | 19 | Thu+Fri / Night 20–23 / late month | down | high |
| 2 | 200 Block Essex St | 0.795 | 248 | 21 | Thu+Fri / Evening Peak 16–19 / early month | down | high |
| 3 | 100 Block Hudson St | 0.737 | 163 | 27 | Mon+Wed / Afternoon 12–15 / late month | down | high |
| 4 | 0 Block Prospect Ave | 0.732 | 173 | 27 | Mon+Thu / Early Morning 00–03 / late month | flat | high |
| 5 | 400 Block Hackensack Ave | 0.643 | 133 | 27 | Tue+Thu / Early Morning 00–03 / early month | flat | high |

All top-10 are high-confidence (≥20 incidents AND ≥6 active months AND ≥10 active weeks).

## Known caveats

- **`trend_90d = down` is a seasonal artifact at the 2026-03-31 anchor.** Last-90d (Jan–Mar 2026) compares to prior-90d (Oct–Dec 2025). Street-disorder volume falls in winter across most locations; a single-cycle `down` is not resolution. Require ≥2 consecutive cycles of decline before concluding a trend.
- **Spatial enrichment deferred:** `lat/long`, `Post`, `PDZone`, and `Grid` are not joined to the top-10 CSV. Use the ArcGIS Pro T4 map to overlay these blocks onto posts/zones before deployment.
- **RMS Feb 2026 data is clean.** The earlier 0-byte stub was re-exported 2026-04-16 and is included in this analysis (see `Docs/data_gaps.md`).
- **Confidence is a qualitative flag, not a calibrated probability.** Bands are volume/persistence gates (high ≥20n & ≥6mo & ≥10wk; medium ≥8n & ≥3mo; low otherwise). Calibration against outcome data is a next-iteration item.
- **Address bucketing risk:** minor entry variance can split one real hotspot across two rows (e.g., `100 Block Main St` vs `100 Main St`). Use map context for ground truth.
- **CAD-side DV out of scope.** Two-layer DV filter runs on RMS only. CAD domestic calls remain in the pool (master prompt §6.7 blind spot).
- **Suspicious calls at severity 2** reflect vigilant callers as much as actual risk; weighting prevents dominance but is not elimination.
- **Not predictive policing.** Historical concentration and recency. Field supervisors ground-truth before deployment.

## Files to brief from

**Command staff (primary):**
- `Docs/deliverables/T4_persistent_hotspots_command_staff.md` — one-pager with top-10 tables + where/when + recommendations + caveats
- `Docs/deliverables/T4_persistent_hotspots_citywide.csv` — top-10 rows, 23-column schema

**Analyst / method backing:**
- `Docs/deliverables/T4_persistent_hotspots_technical_appendix.md` — one-page method + caveats note
- `Scripts/t4/persistent_hotspots.py` — reproducible pipeline
- `_overnight/persistent_hotspots/T4_persistent_hotspots_full_citywide.csv` — all 743 locations for drill-down
- `_overnight/persistent_hotspots/unified_events.csv` — 5,592 filtered CAD+RMS events
- `_overnight/persistent_hotspots/run_stats.json` — run counts + DV exclusion stats

**Reproduce:** `python -m Scripts.t4.persistent_hotspots`

## Next recommended iteration

1. **Confidence calibration** — replace the qualitative high/medium/low gate with a calibrated confidence anchored to outcome data (e.g., CPTED/complaint-resolution follow-up results or next-cycle recurrence). Current gate is conservative but not probabilistic.
2. **ArcGIS overlay** — join top-10 location keys to `latitude/longitude` via CAD raw coordinates, spatial-join to Post/PDZone/Grid polygons, publish hosted feature layer as `T4_Persistent_Hotspots_2024_2026_Q1`, and wire into the T4 Dashboard web map. Delivers the where half visually; pairs with the `deployment_window_recommendation` for the when half.

Secondary (lower priority):
- Seasonality normalization for `trend_90d` — YoY comparison instead of last-90d-vs-prior-90d would remove the seasonal artifact but requires ≥2 full years at each location.
- Address-bucketing dedupe — soft-match `100 Block Main St` vs `100 Main St` to collapse split hotspots (currently requires manual map review).
- CAD-side DV filter — extend the two-layer exclusion to CAD so domestic calls don't inflate residential hotspot scores (master prompt §6.7 follow-up).
