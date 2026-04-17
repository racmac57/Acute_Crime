# T4 Hotspot Analysis — ASAP deliverable brief

**Prepared:** 2026-04-17 (overnight handoff)  
**Audience:** Command / SSOCC / internal stakeholders  
**Code baseline:** `Acute_Crime` `main` @ `0fcbf02` (“t4: DV type keyword filter, NIBRS Tier 2 parsing, decay dtype fix, plan sync”)

---

## Executive summary (read aloud in under two minutes)

1. **Domestic-violence–aware RMS scoring path is implemented** in-repo: standardized case numbers, **blocklist** (`Data/dv_case_numbers_for_t4.csv`) plus **type fallback** so DV-tagged RMS rows are excluded **before** Tier 2-style scoring.
2. **End-to-end Python pipeline** (`python -m Scripts.t4.score_integration`) loads CAD + RMS from `Data/cad` / `Data/rms`, applies DV exclusion, scores locations, and writes **CSV + JSON Data Quality Note** under `Output/<cycle_id>/`.
3. **Operational caveat (transparent):** location keys still use **raw address** as a proxy; **Block_Final** normalization and full **Radio / §6.3** resolution are **not** in this build — called out in the Data Quality Note. This does **not** block delivering **repeatable numbers + audit trail** for a pilot briefing.
4. **PII posture:** production anti-join uses the **PII-safe blocklist CSV only** (not `dv_final_enriched.csv` copied into the project).

---

## What you can hand someone by noon tomorrow

| Artifact | What it proves |
|----------|----------------|
| This brief | Scope, honesty, and what “done” means for this phase |
| `Output/<cycle_id>/<cycle_id>_scored_locations.csv` | Location-level weighted scores after DV filter |
| `Output/<cycle_id>/<cycle_id>_dv_excluded.csv` | Transparency: which RMS rows were excluded and **why** (blocklist vs type) |
| `Output/<cycle_id>/<cycle_id>_data_quality_note.json` | Row counts, exclusion counts, explicit caveats (Radio, Block_Final) |

**Optional one-slide numeric story** (replace with your live run after the command below):

- Example verification window (not a commitment for future months): **~1.7k** RMS rows scoring-ready after **~58** DV exclusions in-sample; **~100+** scored locations (numbers vary by pull window and files on disk).

---

## Morning checklist (before 12:00) — ~15 minutes + run time

1. Open repo: `10_Projects\Acute_Crime`.
2. Confirm `Data\dv_case_numbers_for_t4.csv` exists and CAD/RMS `.xlsx` cover your narrative window.
3. From repo root, run (adjust dates and `cycle_id` to your briefing story):

```bash
python -m Scripts.t4.score_integration ^
  --cycle-id T4_Brief_2026Q1 ^
  --cad-pull-start 2026-03-01 --cad-pull-end 2026-03-28 ^
  --rms-pull-start 2026-03-01 --rms-pull-end 2026-04-11 ^
  --analysis-date 2026-03-28
```

4. Zip **`Output\T4_Brief_2026Q1\`** or paste the **top 15 rows** of `*_scored_locations.csv` into an email appendix.
5. If anything fails: read the **first ERROR** line — usually missing `Data\cad` / `Data\rms` paths, empty month folders, or blocklist path.

---

## What is explicitly *not* claimed in this phase

- Full **master-prompt** parity (precursor correlation, displacement, Power BI export automation, ArcGIS publish).
- **Cycle ID** from `T4_Master_Reporting_Template.xlsx` (workbook does not supply structured cycle codes — use Section 0 / run parameters; see `Docs/t4_cycle_id_strategy.md`).

---

## Suggested one-liner for email cover note

“We implemented and ran a **DV-aware RMS/CAD scoring pipeline** in `Acute_Crime` with **blocklist + incident-type fallback**, **Data Quality JSON**, and **excluded-row transparency**. Outputs are suitable for a **pilot / methods** briefing; **address normalization and Radio linkage** remain the next engineering tranche.”

---

## If asked “when full product?”

Pilot **now**; **full master-prompt alignment** is a **multi-week** effort once **Block_Final + Radio + reporting hooks** are scoped with GIS and command — not a single overnight task.
