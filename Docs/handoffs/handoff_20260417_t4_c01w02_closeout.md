# Handoff — T4 C01W02 closeout (2026-04-17)

## Cycle

- **Cycle ID:** `T4_C01W02`
- **Window:** 2026-03-08 → 2026-03-14 (inclusive, 7-day)

## Tests

- **95 passed** across `_overnight/{A_scoring,B_data_prep,C_output}` (pytest, 1.39s).

## Integration funnel

| Pipeline | Stages |
|----------|--------|
| CAD | loaded 29,324 → in-window 2,300 → whitelist/blacklist 38 → citizen 35 → scoring 32 |
| RMS | loaded 4,388 → in-window 539 → after DV 510 → scoring 2 |

## DV exclusions

| Layer | Count |
|-------|-------|
| Layer 1 — exact case match | 18 |
| Layer 1 — legacy rescue | 0 |
| Layer 2 — type fallback | 11 |

## Output summary

- **29 scored locations** (Section 16, 28 fields, `cycle_id` populated on every row).
- **Top location:** `100 Block Polifly Rd` (weighted 7.5, raw CAD 3, RMS Part 1 0).

## Known limitations (non-blockers)

- `05_EXPORTS/_RMS/monthly/2026/2026_02_RMS.xlsx` is 0 bytes (stub only); the valid re-export lives under `Acute_Crime/Data/rms/monthly/2026_02_RMS.xlsx`. Upstream sync should be refreshed before the next 28-day pull.
- `post` / `pdzone` / `grid` / `latitude` / `longitude` left blank — spatial-join enrichment (§5.5) deferred to a follow-up.

## Release readiness

**Internal-use ready**, with the two caveats above. The Top-5 citywide HTML deliverable from 2026-04-16 remains the command-staff facing artifact; this closeout adds the full 28-field hotspot CSV + DQ note + integration report for internal analytics.

## Next actions

1. Re-export or restore `05_EXPORTS/_RMS/monthly/2026/2026_02_RMS.xlsx` so monthly and 28-day rollups don't silently skip February.
2. Wire spatial-join fallback (§5.5) to fill `pdzone` / `grid` / `lat` / `lon` on the hotspot CSV.
3. Decide whether the T4_C01 (28-day) run should be executed now that the weekly pipeline is green end-to-end.

---

## Files touched this handoff

- `Docs/deliverables/T4_C01W02_hotspots.csv` (promoted)
- `Docs/deliverables/T4_C01W02_data_quality_note.md` (promoted)
- `Docs/deliverables/T4_C01W02_integration_report.md` (promoted)
- `Docs/handoffs/handoff_20260417_t4_c01w02_closeout.md` (this file)
- `Docs/handoffs/session_state.json` (updated)
