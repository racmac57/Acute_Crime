# T4 Hotspot Analysis — Project Summary

**Last updated:** 2026-04-16
**Status:** Design complete. No production code exists. All implementation TODOs are pending.

---

## What This Project Does

T4 Hotspot Analysis is a cycle-aligned crime analysis pipeline for the Hackensack Police Department. It takes CAD and RMS data, scores micro-locations using weighted criteria (call severity, confirmed Part 1 crimes, recency, repeat patterns), classifies each location as Chronic/Persistent/Emerging/Diminishing/One-off, and produces output for:

- **Command staff briefings** — citywide summary, top hotspots by post, deployment recommendations
- **Sergeant-level tactical planning** — directed patrol assignments, CPTED candidates, displacement monitoring
- **Power BI dashboards** — 28-field CSV schema (Section 16 of master prompt)
- **ArcGIS Pro maps and ArcGIS Online publication** — graduated hotspot layers, precursor linkage maps, displacement rings

All analysis is **location/condition-based only**. No individual targeting. No demographic variables. Outputs must be defensible under NJ AG Directive 2021-6, NJ AG Directive 2023-1, and HPD Department Policy.

---

## What Is Complete

### Design Artifacts (100% complete)

1. **Master Prompt v3** (`T4_Hotspot_Analysis_Master_Prompt_v3.md`) — 22 sections covering the full analysis pipeline from run parameters through pre-flight checklist. Defines:
   - Tier 1 CAD scoring (1-5 points by call severity)
   - Tier 2 RMS Part 1 bonus (+1 to +10 by crime type)
   - Recency decay (1.00x to 0.25x by age)
   - Repeat-location boost (1.25x at 3+ incidents)
   - Hotspot classification criteria
   - Precursor correlation (CAD disorder → RMS Part 1 within 14/30 days)
   - Displacement protocol for cooling hotspots
   - 28-field output schema for Power BI and ArcGIS
   - Ethical constraints (non-negotiable)

2. **DV Exclusion Plan** (`Docs/plans/t4_rms_dv_filtering_d5a59b9b.plan.md`) — Two-layer domestic violence filter for RMS preprocessing:
   - Layer 1: Case-number anti-join against `dv_final_enriched.csv`
   - Layer 2: Incident type fallback via `incident_type_map.csv` + `CallType_Categories.csv`
   - Must run before Tier 2 scoring and precursor correlation
   - PII handling rules defined

### Data Available

- **CAD:** 2024-2025 full-year, 2026 Jan-Mar monthly (XLSX in `Data/cad/`)
- **RMS:** 2024-2025 full-year, 2026 Jan and Mar monthly (XLSX in `Data/rms/`; Feb 2026 is empty/0 bytes)
- **City ordinance complaints:** 2024-2026 (CSV in `Data/city_ord/`)
- **Summons:** 2023, 2025-2026 (CSV in `Data/summons/`)
- **Time reports:** 2024-2026 (XLSX in `Data/timereport/`)

---

## What Is Pending

### Implementation TODOs (6 total, all pending)

| # | TODO ID | Description | Blocking? |
|---|---------|-------------|-----------|
| 1 | `confirm-rms-source` | Decide canonical RMS input path and post-normalization column names | Yes — blocks all downstream |
| 2 | `blocklist-pipeline` | Build case_number standardization + anti-join to DV blocklist | Yes — blocks scoring |
| 3 | `type-fallback` | Join IncidentType1/2/3 to incident_type_map; define DV include/exclude list | Yes — blocks scoring |
| 4 | `score-integration` | Wire DV exclusion into Tier 2 and precursor; extend Data Quality Note | Yes — blocks output |
| 5 | `refresh-governance` | Document DV roster refresh cadence; align ValidationConfig with T4 windows | Yes — blocks 2026 runs |
| 6 | `cad-rms-qc-preflight` | (Optional) Run cad_rms_data_quality validators on T4-window exports | No — enhancement |

### Core Pipeline (Not Yet Built)

- No scoring engine (Tier 1 + Tier 2 + decay + boost)
- No address normalization to `Block_Final`
- No `HowReported = Radio` resolution logic
- No hotspot classification engine
- No precursor correlation
- No displacement analysis
- No effectiveness feedback loop
- No Power BI CSV export
- No ArcGIS Pro/Online publishing automation
- No cycle alignment from `T4_Master_Reporting_Template.xlsx`

---

## What Is Needed to Make It Operational

### Minimum Viable Pipeline

1. **Resolve TODO #1** — Confirm whether scripts read from `Data/rms/` XLSX files, AGOL feature class, or a GDB export. Define the canonical column names after snake_case normalization.

2. **Build the DV exclusion module** (TODOs #2-4) — Case blocklist + type fallback, wired before scoring. Must log exclusion counts to Data Quality Note.

3. **Build the scoring engine** — Implement the Section 7 formula: `location_score = [Σ(tier1 × decay) + Σ(tier2 × decay)] × location_boost`

4. **Build address normalization** — `Block_Final` canonical keys per Section 4. Street segment bucketing, intersection alphabetization, suffix standardization.

5. **Build classification logic** — Apply Section 9 criteria in priority order (Chronic → Persistent → Emerging → Diminishing → One-off) using historical cycle data.

6. **Wire cycle alignment** — Read `T4_Master_Reporting_Template.xlsx` (see CLAUDE.md §3 for path) for `cycle_id`, `cycle_7day`, `cycle_28day`. Assert `cycle_id` is non-null before any output.

7. **Build output export** — Generate the 28-field CSV per Section 16 schema + Data Quality Note per Section 17.

### Before First 2026 Run

- **Regenerate DV roster** — `backfill_dv` `ValidationConfig` `date_end` must extend past the T4 analysis window (currently ends 2025-12-31)
- **Verify `T4_Master_Reporting_Template.xlsx`** exists and contains cycle definitions for the target period (see CLAUDE.md §3 for resolved path)
- **Verify `2026_02_RMS.xlsx`** — currently 0 bytes; determine if data is missing or the month had no RMS activity
- **Run Section 22 pre-flight checklist** (16 items) on the first cycle window

### Full Operational Capability

All of the above, plus:
- Precursor correlation (Section 12)
- Displacement analysis (Section 14)
- Effectiveness feedback loop (Section 18)
- ArcGIS Pro layer generation and AGOL publishing (Section 13)
- Map series export by post

---

## Key Risks

1. **DV roster lag** — `dv_final_enriched.csv` data ends **2025-10-29** (~6 months gap). `ValidationConfig` says `date_end = 2025-12-31` but actual data falls short. Any 2026 T4 run requires a `backfill_dv` refresh first.
2. **Column name mismatch** — DV exports use `Case Number` (space); T4 uses `CaseNumber`; must normalize to `case_number`
3. **Empty RMS month** — February 2026 RMS file is 0 bytes; may create a data gap in any cycle spanning that month
4. **No scripts exist** — Everything from data load through output is manual or unbuilt; timeline to operational depends entirely on build velocity
5. **PII exposure** — Any accidental copy of `dv_final_enriched.csv` into this project directory violates PII policy

---

## Author

R. A. Carucci #261, Principal Analyst — SSOCC, Hackensack Police Department
