# T4 Hotspot Analysis — Project Summary

**Last updated:** 2026-04-16
**Status:** Design complete. **Decisions closed in Docs/** (cycle IDs, RMS source default, DV blocklist governance, data gaps, column aliases). **Scoring code** still not built — `type-fallback` + `score-integration` remain.

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
- **RMS:** 2024-2025 full-year, 2026 Jan–Mar monthly (XLSX in `Data/rms/`; Feb 2026 **539 KB** as of 2026-04-16)
- **City ordinance complaints:** 2024-2026 (CSV in `Data/city_ord/`)
- **Summons:** 2023, 2025-2026 (CSV in `Data/summons/`)
- **Time reports:** 2024-2026 (XLSX in `Data/timereport/`)

---

## What Is Pending

### Plan TODOs (snapshot)

| ID | Status |
|----|--------|
| `confirm-rms-source` | **Closed** — [Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md) |
| `blocklist-pipeline` | **Closed** — `Data/dv_case_numbers_for_t4.csv` |
| `refresh-governance` | **Closed** — [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md) |
| `inspect-t4-master-workbook` | **Closed** — CLAUDE §4a |
| `t4-cycle-id-strategy` | **Closed** — [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md) |
| `type-fallback` | **Pending** — code |
| `score-integration` | **Pending** — code |
| `cad-rms-qc-preflight` | Optional |

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
- Cycle labels supplied via **Section 0** ([Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md)) — not from workbook `ReportName` alone

---

## What Is Needed to Make It Operational

### Minimum Viable Pipeline

1. **RMS input** — Default `Data/rms/*.xlsx`; AGOL when matching dashboard ([Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md)).

2. **Build the DV exclusion module** — Load `dv_case_numbers_for_t4.csv` + type fallback; log exclusion counts to Data Quality Note.

3. **Build the scoring engine** — Implement the Section 7 formula: `location_score = [Σ(tier1 × decay) + Σ(tier2 × decay)] × location_boost`

4. **Build address normalization** — `Block_Final` canonical keys per Section 4. Street segment bucketing, intersection alphabetization, suffix standardization.

5. **Build classification logic** — Apply Section 9 criteria in priority order (Chronic → Persistent → Emerging → Diminishing → One-off) using historical cycle data.

6. **Wire cycle alignment** — Populate `cycle_id`, `cycle_7day`, `cycle_28day` from **Section 0** ([Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md)); assert non-null before output.

7. **Build output export** — Generate the 28-field CSV per Section 16 schema + Data Quality Note per Section 17.

### Before First 2026 Run

- **DV blocklist** — `Data/dv_case_numbers_for_t4.csv` through 2026-04-16; refresh per [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md) when new rosters arrive
- **`T4_Master_Reporting_Template.xlsx`** — optional context (CLAUDE §3); **cycle strings from Section 0**
- **`2026_02_RMS.xlsx`** — re-exported; see [Docs/data_gaps.md](Docs/data_gaps.md)
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

1. **DV blocklist currency** — Project CSV extends through **2026-04-16**; refresh per [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md). Upstream `dv_final_enriched` alone still ends **2025-10-29** unless regenerated.
2. **Column name mismatch** — DV exports use `Case Number` (space); T4 uses `CaseNumber`; must normalize to `case_number`
3. **RMS month sync** — Confirm re-exported `2026_02_RMS.xlsx` is present where analysis runs (OneDrive path)
4. **No scripts exist** — Everything from data load through output is manual or unbuilt; timeline to operational depends entirely on build velocity
5. **PII exposure** — Any accidental copy of `dv_final_enriched.csv` into this project directory violates PII policy

---

## Author

R. A. Carucci #261, Principal Analyst — SSOCC, Hackensack Police Department
