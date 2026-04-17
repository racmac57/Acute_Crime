# T4 Persistent Hotspots — Method & Caveats (One-Page)

**Horizon:** 2024-01-01 → 2026-03-31  |  **Analysis date:** 2026-03-31  |  **Locations scored (citywide):** 743  |  **Top 10 delivered.**

## Inputs (read-only)

- CAD: `Data/cad/yearly/2024*.xlsx`, `2025*.xlsx`, `Data/cad/monthly/2026_01..03_CAD.xlsx`
- RMS: `Data/rms/yearly/2024*.xlsx`, `2025*.xlsx`, `Data/rms/monthly/2026_01..03_RMS.xlsx`
- DV blocklist: `Data/dv_case_numbers_for_t4.csv` (1,536 cases; source_date_end max = 2026-04-16)

## Filtering

- **CAD:** keep rows whose `Incident` matches a group/fight severity rule (shots fired 5, aggravated assault 4, fight/group/simple assault 3, disturbance/suspicious 2); exclude `HowReported=Self-Initiated` and dispositions `Unfounded|Canceled|Checked OK`.
- **RMS:** keep NIBRS Part 1 / violent (`09A/B=10, 120=7, 13A=5, 13B=3, 13C=2, 220=3, 240=2`); apply T4 two-layer DV exclusion (Layer 1 case-number blocklist anti-join; Layer 2 type fallback) **before** scoring.
- **Address normalization:** strip city/state/zip, strip unit/apt, standardize suffixes, bucket house numbers to `NNN Block Street`, alphabetize intersections.

## Scoring

Four components per location, each min-max normalized to [0,1]:

1. **frequency** — kept event count
2. **persistence** — distinct year-months with ≥1 event
3. **recency-weighted** — Σ decay(event_date, analysis_date)
4. **severity-weighted** — Σ (severity × decay)

Recency decay: ≤28d=1.00, ≤90d=0.75, ≤180d=0.50, 181+d=0.25.

```
persistent_risk_score = 0.20*freq + 0.30*persistence + 0.20*recency + 0.30*severity
```

Weights tilt toward persistence + severity over raw call volume.

## Qualitative Confidence Flag

- **high** — ≥20 incidents AND ≥6 active months AND ≥10 active weeks
- **medium** — ≥8 incidents AND ≥3 active months
- **low** — everything else (appendix only, do not brief)

## Temporal Bins

- Time-of-day: Early Morning 00–03, Morning 04–07, Morning Peak 08–11, Afternoon 12–15, Evening Peak 16–19, Night 20–23.
- Day-of-month bands: early (1–10), mid (11–20), late (21–31).
- Weekend = Sat+Sun; Weekday = Mon–Fri.
- `trend_90d`: last 90d vs prior 90d; `up` if ratio ≥1.20, `down` if ≤0.80, else `flat`.

## Caveats

- **Event counts:** CAD 4,772 + RMS 835 kept after filters. CAD calls and RMS reports may describe the same incident; scoring weights each source for signal, not as a 1-to-1 event pair.
- **DV exclusion:** 981 RMS rows excluded by case-number blocklist; 1,025 by type fallback. Roster lag means very recent DV may still slip through.
- **`trend_90d = down` is a seasonal artifact for the 2026-03-31 analysis anchor.** last-90d covers Jan–Mar 2026; prior-90d covers Oct–Dec 2025 (higher street-disorder volume). Interpreting one-cycle `down` as hotspot resolution will be wrong at most locations; require ≥2 consecutive cycles of decline before concluding a trend.
- **Spatial enrichment deferred:** lat/long, Post, PDZone, Grid are not joined to output. Use ArcGIS Pro spatial join against raw CAD for overlays.
- **Address-splitting risk:** minor typing differences can split one real hotspot across two rows (e.g., `100 Block Main St` vs `100 Main St`). Use map context.
- **Suspicious calls at low severity (2):** high volume there reflects vigilant callers as much as actual risk; score weighting prevents dominance.
- **CAD-side DV:** master-prompt DV filter runs on RMS only; CAD domestic calls are out of scope for this product.
- **Known source anomaly:** `2026_02_RMS.xlsx` was a 0-byte stub until re-exported 2026-04-16 (see `Docs/data_gaps.md`); any older run would have missed ~539 KB.
- **Not predictive policing.** Historical risk patterning only. Field supervisors ground-truth before deployment decisions.

## Reproducibility

```
python -m Scripts.t4.persistent_hotspots
```

Full citywide CSV (all 743 locations) is cached at `_overnight/persistent_hotspots/T4_persistent_hotspots_full_citywide.csv` for analyst drill-down.