# Integration Report — T4_C01W02

Generated: 2026-04-17T03:21:22

## Stage row counts

| Stage | Count |
|-------|-------|
| cad_loaded | 29324 |
| rms_loaded | 4388 |
| cad_in_window | 2300 |
| rms_in_window | 539 |
| dv_l1_excluded_total | 18 |
| dv_l1_excluded_exact | 18 |
| dv_l1_excluded_rescued | 0 |
| dv_l2_excluded | 11 |
| rms_after_dv | 510 |
| cad_after_whitelist | 38 |
| cad_after_blacklist | 38 |
| cad_citizen | 35 |
| cad_self_init | 3 |
| cad_with_location | 35 |
| cad_scoring | 32 |
| rms_scoring | 2 |
| scored_locations | 29 |

## DV Layer 1 rescue audit

| Metric | Count |
|--------|-------|
| Exact (strict YY-NNNNNN[A]) matches | 18 |
| Rescued (legacy pad/year-collapse/stem) matches | 0 |
| Layer 1 total | 18 |
| Layer 2 (type fallback) | 11 |

## Top 5 scored locations

| Location | Weighted | Raw CAD | RMS Part 1 | Risk |
|----------|----------|---------|------------|------|
| 100 Block Polifly Rd | 7.50 | 3 | 0 | Low |
| 300 Block West Pleasantview Ave | 7.00 | 0 | 1 | Low |
| 300 Block River St | 5.00 | 2 | 0 | Low |
| 100 Block English St | 4.00 | 2 | 0 | Low |
| 100 Block University Plaza Dr | 3.00 | 1 | 0 | Low |

## Outputs

- CSV: `C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\_overnight\integration_out\T4_C01W02\T4_C01W02_hotspots.csv`
- DQ Note: `C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\_overnight\integration_out\T4_C01W02\T4_C01W02_data_quality_note.md`

## Blockers

_none_