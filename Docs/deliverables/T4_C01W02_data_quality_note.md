# T4 Hotspot Analysis — Data Quality Note

**Cycle:** `T4_C01W02`
**Window:** 2026-03-08 → 2026-03-14 (inclusive)
**Generated:** 2026-04-17T03:21:22
**By:** integration.py (cycle T4_C01W02)

---

## 1. Sources

| Layer | Path |
|-------|------|
| CAD pull | `C:\Users\carucci_r\OneDrive - City of Hackensack\05_EXPORTS\_CAD\monthly\2026` |
| RMS pull | `C:\Users\carucci_r\OneDrive - City of Hackensack\05_EXPORTS\_RMS\monthly\2026` |

---

## 2. Volume

| Stage | Count |
|-------|-------|
| CAD rows loaded | 29324 |
| RMS rows loaded | 4388 |
| Scoring rows (final output) | 29 |

---

## 3. DV Exclusion (per §6 DV Exclusion Module)

| Filter | Rows Excluded |
|--------|---------------|
| Layer 1 — Case blocklist (`dv_case_match`) | 18 |
| Layer 2 — Type fallback (`type_fallback`) | 11 |

> Excluded rows never reach Tier 2 scoring or precursor correlation (§6.3).

---

## 4. Call-Type Filtering (§8)

| Decision | Count |
|----------|-------|
| Whitelist kept (citizen-generated focus types) | 38 |
| Blacklist excluded (Medical, MVC, Alarm-Burglar, Parking, etc.) | 2262 |

---

## 5. Pre-Pipeline Quality Scores

| Source | Score |
|--------|-------|
| CAD export | 93.23 / 100 |
| RMS export | 73.53 / 100 |

Per `cad_rms_data_quality/monthly_validation` thresholds. Scores < 90% warrant
operator review before briefing.

---

## 6. Scoring Engine Status

Tier 1 + Tier 2 implemented (overnight A); no precursor/displacement in this integration run

---

## 7. Known Caveats

- DV Layer 1 rescue matched 0 extra rows (legacy case-number forms)
- Intersections geocode to centroid; no coordinate enrichment in this run
- Block_Final uses full_address_2 (CAD) / full_address (RMS) without GIS snap
- post/pdzone/grid blank — spatial-join fallback pending per §5.5

---

## 8. Ethical & Legal Frame

Analysis is location/condition-based only. No individual targeting, no
demographic variables as predictors. Compliant with:

- U.S. Constitution (4th / 14th Amendments)
- NJ AG Directive 2021-6 (Bias-Free Policing)
- NJ AG Directive 2023-1 (Use of Technology in Policing)
- HPD Department Policy

---

*End of Data Quality Note — `T4_C01W02`*
