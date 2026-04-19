# T4 Hotspot Analysis — Hackensack Police Department

Production-grade, cycle-aligned crime analysis pipeline for the Safe Streets Operations Control Center (SSOCC). Generates weighted micro-location hotspot scoring from CAD and RMS data for command staff briefings, sergeant-level tactical deployment, Power BI dashboards, and ArcGIS Pro/Online publication.

**ArcGIS / machine-specific data paths:** If `T4_2026_ArcGIS.aprx` layers break on another PC (e.g. GDB under `C:\TEMP\...`), see [Docs/T4_ArcGIS_data_paths_and_TEMP_mirror.md](Docs/T4_ArcGIS_data_paths_and_TEMP_mirror.md).

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

**Canonical input (closed):** Default pipeline reads **local XLSX** under `Data/rms/`. Use the **AGOL / hosted Calls For Service** layer only when the run must match the published dashboard geometry and attributes exactly — see [Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md) and [CLAUDE.md §3](CLAUDE.md).

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

> **PII RULE:** Never copy `dv_final_enriched.csv` into the `Acute_Crime/` directory. Use **`Data/dv_case_numbers_for_t4.csv`** (PII-safe blocklist: `case_number`, `source`, `source_date_end`) — see [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md). See `dv_doj/docs/pii_policy.md`.

> **Upstream `dv_doj`:** `dv_final_enriched` row-level data historically ended **2025-10-29**; the project blocklist merges PDF supplements through **2026-04-16**. Refresh per [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md) when new rosters ship.

### Supporting References

| Source | Path |
|--------|------|
| Cycle definitions | **Section 0 run parameters** supply `cycle_id` / cycle labels (see [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md)). Reporting workbook path: [CLAUDE.md §3](CLAUDE.md) (`T4_Master_Reporting_Template.xlsx` — context only; `ReportName` may be `T4_Current` only). |
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
│   │   ├── monthly/                           # YYYY_MM_RMS.xlsx
│   │   └── yearly/                            # YYYY_ALL_RMS.xlsx
│   ├── city_ord/                              # City ordinance complaint CSVs
│   ├── summons/                               # E-ticket export CSVs
│   ├── timereport/                            # Personnel shift data
│   └── nibrs/                                 # (empty — pending)
├── Docs/
│   ├── plans/t4_rms_dv_filtering_d5a59b9b.plan.md
│   ├── t4_cycle_id_strategy.md               # Closed: cycle_id from Section 0 run parameters
│   ├── t4_config_and_aliases.md             # RMS source default + HourMinuetsCalc alias table
│   ├── data_gaps.md                          # resolved / residual data notes
│   ├── dv_blocklist_refresh_governance.md
│   └── T4_ArcGIS_data_paths_and_TEMP_mirror.md  # APRX paths, audit/repair, C:\TEMP → OneDrive mirror
├── T4_2026_ArcGIS/                            # ArcGIS Pro project + automation (robocopy mirror, audit/repair scripts)
└── Scripts/                                   # T4 pipeline + Scripts/t4/arcgis/ SOP
```

---

## How to Run

**Scoring engine:** Not built yet. **Design closes:** cycle IDs ([Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md)), RMS source default ([Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md)), DV blocklist (`Data/dv_case_numbers_for_t4.csv`). When scripts are built:

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
| `T4_Master_Reporting_Template.xlsx` | Resolved — see CLAUDE.md §3 | Context workbook; **`cycle_id` from Section 0** — [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md) |
| `summons_etl_normalize.py` | Summons ETL pipeline | Available |
| `Assignment_Master_GOLD.xlsx` | `09_Reference/Personnel/` | Available |

---

## Known Data Gaps

Details: [Docs/data_gaps.md](Docs/data_gaps.md).

- **`2026_02_RMS.xlsx`** — **Re-exported (2026-04-16); verified ~539 KB** — [Docs/data_gaps.md](Docs/data_gaps.md).
- **`Data/nibrs/`** — empty (pending).
- **T4 workbook** — `ReportName` = `T4_Current` only; structured **`cycle_id` comes from Section 0** per [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md). Spaced headers; **`HourMinuetsCalc`** typo → alias in [Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md).
- **Scoring code** — still pending; DV exclusion design is in [Docs/plans/t4_rms_dv_filtering_d5a59b9b.plan.md](Docs/plans/t4_rms_dv_filtering_d5a59b9b.plan.md).

---

## Author

R. A. Carucci #261, Principal Analyst — Safe Streets Operations Control Center, Hackensack Police Department
