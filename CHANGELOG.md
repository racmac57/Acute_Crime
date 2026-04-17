# Changelog

All notable changes to the T4 Hotspot Analysis project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Changed (2026-04-16)

- **`2026_02_RMS.xlsx`** — Operator re-exported February 2026 RMS (replacing 0-byte placeholder); **verified 539 KB** on disk. [Docs/data_gaps.md](Docs/data_gaps.md), README, CLAUDE §24 updated.

### Added (2026-04-16 — close remaining operator/build table items)

- [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md) — **Cycle ID generation closed:** `cycle_id` / `cycle_7day` / `cycle_28day` authoritative from **Section 0**; workbook `T4_Current` is context-only
- [Docs/data_gaps.md](Docs/data_gaps.md) — **`2026_02_RMS.xlsx`** 0-byte gap documented (operator actions)
- [Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md) — **`confirm-rms-source` closed:** default local `Data/rms/*.xlsx` vs AGOL; copy-paste **`config/t4_defaults.yaml`** block; **`HourMinuetsCalc`** → canonical `hour_minuets_calc` alias table
- [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md) — refresh rules for `Data/dv_case_numbers_for_t4.csv`
- README + CLAUDE updated for the above (cycle_id source, RMS canonical input, §13 cycle reporting)

### Fixed (2026-04-16 — doc consistency pass)

- README pre-flight checklist count corrected: was "22 items", now references Master Prompt §22 (16 items) and CLAUDE.md §22 (20 items with 4 DV extensions)
- `T4_Master.xlsx` path resolved across all docs — active file is `T4_Master_Reporting_Template.xlsx` at `Documents\Projects\T4_New\T4_Master_Query\`; original archived. Full path in CLAUDE.md §3; README/SUMMARY reference CLAUDE.md §3
- Plan crosswalk section updated: checklist count row marked corrected; T4_Master path row updated with resolved location
- SUMMARY references to `T4_Master.xlsx` updated to `T4_Master_Reporting_Template.xlsx` with CLAUDE.md §3 pointer
- Filename consistency pass: remaining prose `T4_Master.xlsx` references in README and CLAUDE.md updated to use operational filename or generic "T4 Master workbook"; legacy-name note added to both files explaining the master prompt uses `T4_Master.xlsx` while the file on disk is `T4_Master_Reporting_Template.xlsx`

### Added (2026-04-16 — gate inspection results)

- **Gate 2 CLOSED:** T4 Master workbook inspected — 11 sheets documented in CLAUDE.md §4a. Key findings: `ReportName` contains only `T4_Current` (not structured cycle IDs); column names use spaces; time fields are Excel serial numbers; `HourMinuetsCalc` is misspelled in source
- **Gate 3a CONFIRMED:** `2026_02_RMS.xlsx` is 0 bytes (placeholder created 2026-02-03, no data)
- **Gate 3b CONFIRMED:** DV roster actual data ends **2025-10-29** (1,322 rows), not 2025-12-31 as `ValidationConfig` implies — ~6 month gap to present. All docs updated with corrected date.
- CLAUDE.md §4a added with full sheet inventory, column names, and data format notes
- README, SUMMARY known-data-gaps sections updated with inspection results
- `09_Reference/Standards` confirmed as source for Gates 1 and 4 (RMS field definitions, UCR/NIBRS mapping, normalization maps)

### Added (2026-04-16 — DV blocklist extraction)

- Extracted 215 case numbers (222 pages matched, 7 duplicates → 215 unique) from `2025_10_29_to_2026_04_16_DV_roster.pdf` (223 pages, FileMaker Pro export with embedded text layer)
- Page 216 missing case number in text layer (incident 04/11/26, P.O. Andres Lopez 375) — resolved manually as `26-033051`
- Created `Data/dv_case_numbers_for_t4.csv` — **1,536 unique case numbers** combined from `dv_final_enriched.csv` (1,322, through 2025-10-29) and PDF extraction (213 new, through 2026-04-16). PII-safe: 3 columns only (`case_number`, `source`, `source_date_end`)
- DV blocklist now covers 2023-01-01 through 2026-04-16 — sufficient for current T4 analysis windows
- CLAUDE.md §6.4 and §6.5 updated with combined blocklist status

### Pending — DV Exclusion Module (plan todos)

- `confirm-rms-source` — **Closed** in [Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md) (default local RMS vs AGOL)
- `blocklist-pipeline` — **Closed** — `Data/dv_case_numbers_for_t4.csv` exists
- `type-fallback` — **Pending code**
- `score-integration` — **Pending code**
- `refresh-governance` — **Closed** — [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md)
- `cad-rms-qc-preflight` — (Optional) Run `cad_rms_data_quality` when using raw exports

### Pending — Core Pipeline

- No production scoring scripts exist yet
- No address normalization (`Block_Final`) implementation
- No `HowReported = Radio` resolution logic implemented
- No cycle alignment from T4 Master workbook (`T4_Master_Reporting_Template.xlsx`) wired in
- No ArcGIS Pro/Online publishing workflow scripted
- No Power BI CSV export generation
- No displacement analysis automation
- No effectiveness feedback loop automation

---

## [v0.3.0] — 2026-04-16

### Added

- `README.md` — Project overview, data sources, folder structure, run parameters, ETL dependencies
- `CHANGELOG.md` — This file
- `SUMMARY.md` — Plain-language project status summary
- `CLAUDE.md` — Full agent-ready project instructions (all 22 Master Prompt sections + DV module)

---

## [v0.2.0] — 2026-04-16

### Added

- `Docs/plans/t4_rms_dv_filtering_d5a59b9b.plan.md` — Two-layer DV exclusion implementation plan
  - Case-number anti-join against `dv_final_enriched.csv`
  - Incident type fallback via `incident_type_map.csv` + `CallType_Categories.csv`
  - Mermaid flowchart of exclusion pipeline
  - Blind spots analysis (roster lag, over/under-exclusion, PII handling)
  - 6 pending TODOs defined

### Added (Data)

- `Data/cad/monthly/` — 2026-01 through 2026-03 CAD exports (XLSX)
- `Data/cad/yearly/` — 2024 and 2025 full-year CAD exports (XLSX)
- `Data/rms/monthly/` — 2026-01 and 2026-03 RMS exports (XLSX); 2026-02 is 0 bytes
- `Data/rms/yearly/` — 2024 and 2025 full-year RMS exports (XLSX)
- `Data/city_ord/` — 2024-2026 city ordinance complaint CSVs
- `Data/summons/` — 2023, 2025-2026 e-ticket export CSVs
- `Data/timereport/` — 2024-2026 personnel time report XLSX files

---

## [v0.1.0] — 2026-04-16

### Added

- `T4_Hotspot_Analysis_Master_Prompt_v3.md` — Complete master prompt defining:
  - Section 0: Run parameters template
  - Sections 1-2: Role and context
  - Section 3: Data sources and preprocessing rules
  - Section 4: Location normalization (`Block_Final`)
  - Section 5: Focus call types (whitelist)
  - Section 6: Exclusions (blacklist, disposition, self-initiated)
  - Section 7: Weighted scoring model (Tier 1 CAD + Tier 2 RMS Part 1 + recency decay + repeat-location boost)
  - Section 8: Time analysis (6 fixed bins)
  - Section 9: Hotspot classification (Chronic / Persistent / Emerging / Diminishing / One-off)
  - Section 10: Posts/districts with target hotspot counts
  - Section 11: Cycle-aligned reporting (7-day, 28-day, YTD)
  - Section 12: CAD-RMS precursor correlation (14-day primary / 30-day extended)
  - Section 13: GIS workflow (Kernel Density, Getis-Ord Gi*, Emerging Hot Spot, Local Moran's I)
  - Section 14: Displacement analysis protocol
  - Section 15: Output format (citywide summary, post details, deployment recommendations, confidence ratings)
  - Section 16: 28-field output integration schema (CSV / JSON / GeoJSON / Feature Class)
  - Section 17: Data quality checks (11 required checks)
  - Section 18: Effectiveness feedback loop
  - Section 19: Output constraints
  - Section 20: Blind spots and pitfalls (9 documented)
  - Section 21: Ethical constraints (non-negotiable)
  - Section 22: Pre-flight checklist (16 items)
- `Acute_Crime.code-workspace` — VS Code workspace configuration
