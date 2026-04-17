# T4 Hotspot Analysis — Hackensack Police Department

Production-grade, cycle-aligned crime analysis pipeline for the Safe Streets Operations Control Center (SSOCC). Generates weighted micro-location hotspot scoring from CAD and RMS data for command staff briefings, sergeant-level tactical deployment, Power BI dashboards, and ArcGIS Pro/Online publication.

---

## Purpose

Analyze Hackensack PD CAD (Computer-Aided Dispatch) and RMS (Records Management System) data to identify actionable micro-place hotspots for group activity, violence, disorder, and ordinance-related issues. Output is cycle-aligned to HPD's T4 framework (7-day and 28-day cycles defined in the T4 Master workbook).

> **Filename note:** The Master Prompt references `T4_Master.xlsx`. The operational file on disk is `T4_Master_Reporting_Template.xlsx` (see CLAUDE.md §3 for full path). Both names refer to the same cycle-definition workbook.

**This is location/condition analysis only.** No individual targeting, no demographic variables. Defensible under U.S. Constitution (4th/14th Amendments), NJ AG Directive 2021-6, NJ AG Directive 2023-1, and HPD Department Policy.

---

## Data Sources

### CAD (Computer-Aided Dispatch)

| Source | Path |
|--------|------|
| Monthly exports | `Data/cad/monthly/YYYY_MM_CAD.xlsx` |
| Yearly exports | `Data/cad/yearly/YYYY_CAD_ALL.xlsx` |
| AGOL feature class | `HPD2022LAWSOFT` daily append (565K+ records) |

**Key fields:** `ReportNumberNew`, `Incident`, `HowReported`, `FullAddress2`, `PDZone`, `Grid`, `TimeOfCall`, `TimeDispatched`, `TimeOut`, `TimeIn`, `Officer`, `Disposition`, `latitude`, `longitude`

### RMS (Records Management System)

| Source | Path |
|--------|------|
| Monthly exports | `Data/rms/monthly/YYYY_MM_RMS.xlsx` |
| Yearly exports | `Data/rms/yearly/YYYY_ALL_RMS.xlsx` |

**Key fields:** `CaseNumber`, `IncidentType1`, `IncidentType2`, `IncidentType3`, `UCRCode`, `FullAddress`, `IncidentDate`, `IncidentTime`, `Narrative`

**Column name warning:** DV pipeline exports use `Case Number` (with space); T4 uses `CaseNumber`. Normalize both to `case_number` before any join.

### DV Blocklist (External — Do NOT Copy Full File Here)

| Source | Path |
|--------|------|
| Primary blocklist | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\dv_doj\processed_data\dv_final_enriched.csv` |
| Incident type map | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\dv_doj\docs\mappings\incident_type_map.csv` |
| CAD call type ref | `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv` |
| Normalization pattern | `backfill_dv.py` → `standardise_case_number()`, regex `^\d{2}-\d{6}$` |
| PII policy | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\dv_doj\docs\pii_policy.md` |

> **PII RULE:** Never copy `dv_final_enriched.csv` into the `Acute_Crime/` directory. Use a minimal derived file (`dv_case_numbers_for_t4.csv` — single `case_number` column + optional `source_file_date`) or a config path pointer. See `dv_doj/docs/pii_policy.md`.

> **ROSTER LAG:** `backfill_dv` `ValidationConfig` currently ends `2025-12-31`. The DV roster must be regenerated before running any 2026 T4 analysis window.

### Supporting References

| Source | Path |
|--------|------|
| Cycle definitions | `T4_Master_Reporting_Template.xlsx` — see CLAUDE.md §3 for resolved path (provides `cycle_id`, `ReportName`, 7-day/28-day labels) |
| Personnel | `09_Reference/Personnel/Assignment_Master_GOLD.xlsx` |
| Summons ETL output | `summons_slim_for_powerbi.csv` via `summons_etl_normalize.py` |
| City ordinance complaints | `Data/city_ord/` |
| Field schemas | `09_Reference/Standards/CAD_RMS/DataDictionary/current/schema/` |

---

## Folder Structure

```
Acute_Crime/
├── T4_Hotspot_Analysis_Master_Prompt_v3.md   # Master prompt (v3) — scoring, classification, output spec
├── README.md                                  # This file
├── CHANGELOG.md                               # Version history
├── SUMMARY.md                                 # Plain-language project summary
├── CLAUDE.md                                  # Agent-ready project instructions
├── Acute_Crime.code-workspace                 # VS Code workspace
├── Data/
│   ├── cad/
│   │   ├── monthly/                           # YYYY_MM_CAD.xlsx
│   │   └── yearly/                            # YYYY_CAD_ALL.xlsx
│   ├── rms/
│   │   ├── monthly/                           # YYYY_MM_RMS.xlsx (NOTE: 2026_02 is 0 bytes)
│   │   └── yearly/                            # YYYY_ALL_RMS.xlsx
│   ├── city_ord/                              # City ordinance complaint CSVs
│   ├── summons/                               # E-ticket export CSVs
│   ├── timereport/                            # Personnel shift data
│   └── nibrs/                                 # (empty — pending)
├── Docs/
│   └── plans/
│       └── t4_rms_dv_filtering_d5a59b9b.plan.md  # DV exclusion implementation plan
└── Scripts/                                   # (pending — ETL and scoring scripts)
```

---

## How to Run

**No production scripts exist yet.** The project is in design/documentation phase. When scripts are built:

### Pre-Flight (Every Run)

1. Populate all Section 0 Run Parameters (`cycle_id`, pull dates, `analysis_date`, `prior_cycle_id`)
2. Run the pre-flight checklist — Master Prompt v3 §22 defines 16 items; CLAUDE.md §22 adds 4 DV-related items (20 total) for implementation runs. Use CLAUDE.md §22 as the operational checklist.
3. Verify DV roster covers the analysis window (`max(IncidentDate)` in `dv_final_enriched.csv` must be >= `rms_pull_start`)
4. Verify `T4_Master_Reporting_Template.xlsx` contains the target `cycle_id` (see CLAUDE.md §3 for path)
5. Confirm CAD/RMS exports exist for the full pull window with no gaps

### Run Parameters

| Parameter | Description |
|-----------|-------------|
| `run_date` | YYYY-MM-DD — execution date |
| `operator` | R. A. Carucci or delegated analyst name |
| `cycle_id` | From `T4_Master_Reporting_Template.xlsx` (e.g., `T4_C01W02`) — **mandatory on all outputs** |
| `cad_pull_start` | YYYY-MM-DD — start of CAD window |
| `cad_pull_end` | YYYY-MM-DD — end of CAD window |
| `rms_pull_start` | YYYY-MM-DD — same window as CAD |
| `rms_pull_end` | YYYY-MM-DD + 14-day buffer for precursor check |
| `analysis_date` | Date used as "today" for recency decay |
| `prior_cycle_id` | For cycle-over-cycle delta comparison |

**Rule:** If any parameter is blank, halt. Outputs without `cycle_id` are invalid for T4 briefings.

### Expected Pipeline Order (When Built)

1. Load and validate CAD/RMS exports (snake_case normalization, dedup, field validation)
2. Apply DV exclusion (blocklist anti-join → type fallback → log exclusion counts)
3. Apply call-type whitelist/blacklist and disposition exclusions
4. Resolve `HowReported = Radio` entries (citizen vs. self-initiated)
5. Normalize addresses to `Block_Final` canonical keys
6. Compute Tier 1 (CAD) + Tier 2 (RMS Part 1) scores with recency decay
7. Apply repeat-location boost
8. Classify hotspots (Chronic / Persistent / Emerging / Diminishing / One-off)
9. Run precursor correlation (14-day primary / 30-day extended)
10. Run displacement check on Diminishing locations
11. Run effectiveness feedback (prior-cycle Top 5 comparison)
12. Generate Data Quality Note
13. Export to CSV (Power BI), GeoJSON, Feature Class (ArcGIS)
14. Publish to ArcGIS Online

---

## ETL Dependencies

| Dependency | Source | Status |
|------------|--------|--------|
| CAD ETL pipeline | `HPD2022LAWSOFT` Task Scheduler | Running (daily append) |
| `cad_rms_data_quality` validators | `02_ETL_Scripts/cad_rms_data_quality/` | Available — use as pre-flight QC |
| DV blocklist pipeline (`backfill_dv`) | `02_ETL_Scripts/dv_doj/` | Needs refresh past 2025-12-31 |
| `incident_type_map.csv` | `02_ETL_Scripts/dv_doj/docs/mappings/` | Available |
| `CallType_Categories.csv` | `09_Reference/Classifications/CallTypes/` | Available |
| `T4_Master_Reporting_Template.xlsx` | Resolved — see CLAUDE.md §3 for full path | Required for cycle_id |
| `summons_etl_normalize.py` | Summons ETL pipeline | Available |
| `Assignment_Master_GOLD.xlsx` | `09_Reference/Personnel/` | Available |

---

## Known Data Gaps

- `Data/rms/monthly/2026_02_RMS.xlsx` is 0 bytes (empty file)
- `Data/nibrs/` is empty — no NIBRS data loaded
- DV roster (`dv_final_enriched.csv`) ends 2025-12-31 — must be regenerated for 2026 windows
- T4 Master workbook inspected 2026-04-16 — `ReportName` contains only `T4_Current`, not `T4_C01W02` cycle IDs. Cycle ID generation needed. See CLAUDE.md §4a.
- DV roster (`dv_final_enriched.csv`) actual data ends **2025-10-29** — ~6 months short. `backfill_dv` refresh required before any T4 run.
- T4 Master column names use spaces (`How Reported`, `Time of Call`) — snake_case normalization must handle both spaced and camelCase variants.
- No production scoring scripts exist yet — all 6 implementation TODOs are pending

---

## Author

R. A. Carucci #261, Principal Analyst — Safe Streets Operations Control Center, Hackensack Police Department
