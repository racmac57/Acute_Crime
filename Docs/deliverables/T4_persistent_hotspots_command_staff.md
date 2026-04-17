# T4 Persistent Hotspots — Command Staff Briefing

**Horizon:** 2024-01-01 through 2026-03-31 (analysis date 2026-03-31)
**Scope:** group/fight/disorder-relevant CAD incidents + RMS Part 1 violent crimes at same locations
**Classification:** Law Enforcement Sensitive. Location-based, condition-focused. No individual targeting.

## Purpose

Historical risk patterning to inform targeted patrol allocation (where + when). This is evidence-based persistence analysis, not deterministic prediction. Outputs are advisory — field supervisors validate ground truth before deployment decisions.

## Top 10 Persistent Hotspots

| # | Location | Risk | Incidents | Months Active | Trend 90d | Confidence |
|---|---|---:|---:|---:|---|---|
| 1 | 0 Block Newman St | 0.908 | 297 | 19 | down | high |
| 2 | 200 Block Essex St | 0.795 | 248 | 21 | down | high |
| 3 | 100 Block Hudson St | 0.737 | 163 | 27 | down | high |
| 4 | 0 Block Prospect Ave | 0.732 | 173 | 27 | flat | high |
| 5 | 400 Block Hackensack Ave | 0.643 | 133 | 27 | flat | high |
| 6 | 500 Block South River St | 0.560 | 106 | 26 | down | high |
| 7 | 100 Block Essex St | 0.528 | 83 | 26 | flat | high |
| 8 | 200 Block Prospect Ave | 0.477 | 76 | 26 | down | high |
| 9 | 100 Block River St | 0.461 | 71 | 26 | down | high |
| 10 | 300 Block Union St | 0.460 | 65 | 24 | flat | high |

## Where + When — Deployment Windows (Top 10)

| # | Location | Top Day(s) | Top Time Window | Day-of-Month | Weekend Share | Confidence |
|---|---|---|---|---|---:|---|
| 1 | 0 Block Newman St | Thu + Fri | Night 20-23 | late (21-31) | 20% | high |
| 2 | 200 Block Essex St | Thu + Fri | Evening Peak 16-19 | early (1-10) | 25% | high |
| 3 | 100 Block Hudson St | Mon + Wed | Afternoon 12-15 | late (21-31) | 21% | high |
| 4 | 0 Block Prospect Ave | Mon + Thu | Early Morning 00-03 | late (21-31) | 25% | high |
| 5 | 400 Block Hackensack Ave | Tue + Thu | Early Morning 00-03 | early (1-10) | 28% | high |
| 6 | 500 Block South River St | Tue + Thu | Early Morning 00-03 | mid (11-20) | 24% | high |
| 7 | 100 Block Essex St | Mon + Wed | Early Morning 00-03 | early (1-10) | 28% | high |
| 8 | 200 Block Prospect Ave | Sat + Wed | Early Morning 00-03 | late (21-31) | 37% | high |
| 9 | 100 Block River St | Fri + Tue | Early Morning 00-03 | mid (11-20) | 24% | high |
| 10 | 300 Block Union St | Thu + Fri | Afternoon 12-15 | mid (11-20) | 8% | high |

## Operational Recommendations

1. **Deploy against top-DOW / top-time window first.** Focus directed patrol on each hotspot's highest-concentration window before spreading resources to secondary windows.
2. **Re-validate 'up-trend' hotspots in the next cycle.** Locations flagged `trend_90d = up` with medium+ confidence warrant supervisor ground-truth check and potential CPTED or landlord/business contact.
3. **Treat low-confidence rows as appendix only.** Do not brief `confidence_band = low` locations as hotspots; they are listed for analyst awareness, not deployment targets.

## Caveats (Plain Language)

- Scoring mixes calls (CAD) and reports (RMS). Some records describe the same incident; the score weights each source for its signal, not for a one-to-one event count.
- Domestic-violence records are excluded via the T4 two-layer filter. Roster lag means very recent DV cases may still be present.
- Suspicious-person / suspicious-vehicle calls are included at low severity. High volume at those call types can reflect vigilant callers as much as actual risk.
- Address normalization buckets to 100-block segments; minor differences in how addresses were entered can split a real hotspot across two rows. Use map context for ground truth.
- **`trend_90d = down` is largely a seasonal artifact.** The last 90 days (Jan–Mar 2026) compares to the prior 90 days (Oct–Dec 2025). Street-disorder volume falls in winter across most locations — a `down` flag here does **not** mean the hotspot is resolving. Sustained multi-cycle decline is the signal; one cycle is not.
- **Spatial enrichment deferred:** lat/long, Post, PDZone, and Grid are not joined to these rows. Use the ArcGIS Pro T4 map to overlay these locations onto posts/zones before deployment.
- **RMS Feb 2026 data is now clean.** The earlier 0-byte stub was re-exported 2026-04-16 and is included in this analysis (see `Docs/data_gaps.md`).
- This is not predictive policing. It describes historical concentration and recency, not individuals or future certainty.

_Generated from 4,772 CAD events + 835 RMS events across 743 distinct locations._