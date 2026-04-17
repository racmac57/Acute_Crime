# CLAUDE.md — T4 Hotspot Analysis (Full Project Instructions)

This file is the complete agent-ready reference for the T4 Hotspot Analysis system. A fresh Claude session should be able to pick up this project cold with no prior context.

**Project owner:** R. A. Carucci #261, Principal Analyst — Safe Streets Operations Control Center (SSOCC), Hackensack Police Department, NJ.

**Last updated:** 2026-04-16

> **Filename note:** The Master Prompt references `T4_Master.xlsx`. The operational file on disk is **`T4_Master_Reporting_Template.xlsx`** (full path in §3 External Dependencies). Both names refer to the same cycle-definition workbook. Prose references to `T4_Master.xlsx` in this file follow the master prompt's naming convention; scripts must use the actual filename.

---

## 1. Project Purpose

T4 Hotspot Analysis is a production-grade, cycle-aligned crime analysis pipeline. It scores micro-locations using weighted CAD and RMS data, classifies hotspots, correlates precursor patterns, checks for displacement, and produces outputs for command staff briefings, Power BI dashboards, and ArcGIS Pro/Online maps.

**Ethical constraint (non-negotiable):** Analysis is location/condition-based only. No individual targeting. No demographic variables as predictors. All outputs must be defensible under U.S. Constitution (4th/14th Amendments), NJ AG Directive 2021-6 (Bias-Free Policing), NJ AG Directive 2023-1 (Use of Technology in Policing), and HPD Department Policy.

---

## 2. Project Status

**Design:** Complete (Master Prompt v3 + DV Exclusion Plan + [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md)).
**Implementation:** Scoring engine not built; **closed decisions:** cycle IDs (Section 0), canonical RMS default (local `Data/rms/` vs AGOL — [Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md)), DV blocklist at `Data/dv_case_numbers_for_t4.csv`.
**Data:** CAD/RMS layouts under `Data/`; **`dv_case_numbers_for_t4.csv`** through 2026-04-16; refresh per [Docs/dv_blocklist_refresh_governance.md](Docs/dv_blocklist_refresh_governance.md).

---

## 3. Path Resolution

**Canonical OneDrive root:** `C:\Users\carucci_r\OneDrive - City of Hackensack`

Always use `carucci_r` in paths. Never use `RobertCarucci`.

### Project Paths

| Resource | Path |
|----------|------|
| Project root | `C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\` |
| Master prompt | `{project_root}\T4_Hotspot_Analysis_Master_Prompt_v3.md` |
| DV exclusion plan | `{project_root}\Docs\plans\t4_rms_dv_filtering_d5a59b9b.plan.md` |
| CAD monthly | `{project_root}\Data\cad\monthly\` |
| CAD yearly | `{project_root}\Data\cad\yearly\` |
| RMS monthly | `{project_root}\Data\rms\monthly\` |
| RMS yearly | `{project_root}\Data\rms\yearly\` |
| City ordinance | `{project_root}\Data\city_ord\` |
| Summons | `{project_root}\Data\summons\` |
| Time reports | `{project_root}\Data\timereport\` |

### External Dependencies (Do Not Copy Into Project)

| Resource | Path |
|----------|------|
| DV blocklist (PII) | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\dv_doj\processed_data\dv_final_enriched.csv` |
| DV normalization code | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\dv_doj\etl_scripts\backfill_dv.py` |
| Incident type map | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\dv_doj\docs\mappings\incident_type_map.csv` |
| CAD call type ref | `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv` |
| PII policy | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\dv_doj\docs\pii_policy.md` |
| CAD/RMS validators | `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\cad_rms_data_quality\` |
| Personnel | `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Personnel\Assignment_Master_GOLD.xlsx` |
| Field schemas | `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Standards\CAD_RMS\DataDictionary\current\schema\` |
| T4 cycle workbook | `C:\Users\carucci_r\OneDrive - City of Hackensack\Documents\Projects\T4_New\T4_Master_Query\T4_Master_Reporting_Template.xlsx` (68 KB, 11 sheets — see §4a below); archived original at `...\T4_Master_Query\_Archived\T4_Master.xlsm` |
| AGOL feature class | `HPD2022LAWSOFT` daily append (565K+ records) |
| AGOL CFS service URL | `https://services1.arcgis.com/JYl0Hy0wQdiiV0qh/arcgis/rest/services/CallsForService_2153d1ef33a0414291a8eb54b938507b/FeatureServer/0` |

---

## 4. Run Parameters (Section 0)

Every analysis run requires these parameters populated before any processing begins. If any parameter is blank, halt.

| Parameter | Format | Description |
|-----------|--------|-------------|
| `run_date` | YYYY-MM-DD | Execution date |
| `operator` | string | R. A. Carucci or delegated analyst name |
| `cycle_id` | string | **Section 0 / analyst entry** (e.g. `T4_C01W02`) — **mandatory on all outputs**. *Not* read from `T4_Master_Reporting_Template.xlsx` `ReportName` (currently `T4_Current` only) — see [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md). |
| `cad_pull_start` | YYYY-MM-DD | Start of CAD data window |
| `cad_pull_end` | YYYY-MM-DD | End of CAD data window |
| `rms_pull_start` | YYYY-MM-DD | Same window as CAD |
| `rms_pull_end` | YYYY-MM-DD | CAD end + 14-day buffer (for precursor check) |
| `analysis_date` | YYYY-MM-DD | Date used as "today" for recency decay calculation |
| `prior_cycle_id` | string | For cycle-over-cycle delta |

**Rule:** Outputs without `cycle_id` are invalid for T4 briefings.

### 4a. T4 Master Workbook — Inspected 2026-04-16

**File:** `T4_Master_Reporting_Template.xlsx` (68 KB, modified 2025-05-28)

**11 sheets** (4 with data, 5 empty stubs, 2 query/connection):

| Sheet | Rows | Purpose |
|-------|------|---------|
| `CAD_T4` | 194 | Primary CAD data for current cycle (20 columns — same as CAD export) |
| `QA_Excluded_Locations` | 31 | Records excluded from analysis (same 20 columns) |
| `Summary_By_Block_TOD_Platoon_Sq` | 56 | Aggregated by block + time-of-day + platoon: `ReportName`, `Block`, `TimeOfDay`, `Platoon`, `Call_Count`, `Avg_Response_Minutes`, `Avg_OnScene_Minutes` |
| `Summary_By_Block_TOD` | 50 | Simplified: `Block`, `TimeOfDay`, `Count` |
| `CAD4FIX` | stub | External data connection |
| `Query1` | stub | Power Query connection |
| `CAD_T4_Imported` | stub | Empty |
| `CAD_T4_Transformed` | stub | Empty |
| `Cycle_Summary` | stub | Empty |
| `Visual_Export` | stub | Empty |
| `Query_Notes` | stub | Empty |

**Key findings:**
- `ReportName` column currently contains only `T4_Current` — **not** structured `T4_C01W02` cycle IDs. The cycle ID format from the master prompt either needs to be generated by pipeline code or sourced from a separate cycle calendar.
- CAD columns use **spaces** in names: `How Reported`, `Time of Call`, `Time Dispatched`, `Time Out`, `Time In`, `Time Spent`, `Time Response`, `Response Type`. Snake_case normalization must handle both spaced and camelCase variants.
- Time fields are **Excel serial numbers** (e.g., `45784.0981712963`), not text datetime strings.
- `cYear` is text string (e.g., `"2025"`), `cMonth` is month name (e.g., `"May"`).
- `HourMinuetsCalc` (note: misspelled "Minuets") contains `HH:MM` strings — map to canonical snake_case per [Docs/t4_config_and_aliases.md](Docs/t4_config_and_aliases.md) (e.g. `hour_minuets_calc`).

---

## 5. Data Sources and Fields

### 5.1 CAD Fields (Section 3.1)

`ReportNumberNew`, `Incident`, `HowReported`, `FullAddress2`, `PDZone`, `Grid`, `TimeOfCall`, `TimeDispatched`, `TimeOut`, `TimeIn`, `TimeSpent`, `TimeResponse`, `Officer`, `Disposition`, `ResponseType`, `CADNotes`

Coordinates: `latitude`, `longitude` (present in exports; see ESRI backfill CLAUDE.md for details).

### 5.2 RMS Fields (Section 3.2)

`CaseNumber`, `IncidentType1`, `IncidentType2`, `IncidentType3`, `FullAddress`, `IncidentDate`, `IncidentTime`, `UCRCode`, `Narrative`

Fallbacks: `IncidentDate` → `ReportDate`; `IncidentTime` → `ReportTime`.

### 5.3 Column Name Pitfalls

| Source | Raw Column | Normalized (snake_case) |
|--------|-----------|------------------------|
| RMS export | `CaseNumber` | `case_number` |
| DV pipeline export | `Case Number` (with space) | `case_number` |
| CAD export | `ReportNumberNew` | `report_number_new` |
| CAD export | `HowReported` | `how_reported` |
| CAD export | `FullAddress2` | `full_address_2` |
| RMS export | `IncidentType1` | `incident_type_1` |

**Critical:** DV pipeline may use `Case Number` (space). T4 master prompt uses `CaseNumber` (no space). Normalize both to `case_number` before any join. Use `backfill_dv.py` → `standardise_case_number()` pattern: strip whitespace, uppercase, validate regex `^\d{2}-\d{6}$`.

### 5.4 Preprocessing Rules (Section 3.4)

1. Normalize all field names to `snake_case`
2. Combine `IncidentType1/2/3` into a single `all_incidents` array
3. Standardize addresses: CAD → `FullAddress2`, RMS → `FullAddress`
4. Strip apartment/unit numbers before grouping
5. Standardize street suffixes (St/Street, Ave/Avenue, Pl/Place, Blvd/Boulevard)
6. Group similar addresses into one canonical location key (`Block_Final`)

### 5.5 Fallback Logic (Section 3.5)

| Missing Field | Fallback |
|---------------|----------|
| `IncidentDate` | Use `ReportDate` |
| `IncidentTime` | Use `ReportTime` |
| `PDZone` | Spatial-join to zone polygon via coordinates |
| Location | Exclude from scoring; track count in Data Quality Note |
| `UCRCode` | Derive from `IncidentType1` using UCR/NIBRS mapping table |

---

## 6. DV Exclusion Module

### 6.1 Purpose

Remove domestic violence cases from RMS data before hotspot scoring. DV incidents are household-intimate, not street-disorder — including them skews micro-place scoring toward residential addresses and conflicts with the location/problem-solving framing.

### 6.2 Two-Layer Filter

**Layer 1 — Case Blocklist (anti-join):**
- Load `dv_final_enriched.csv` → extract `CaseNumber` column → normalize via `standardise_case_number()` → deduplicate → produces blocklist
- Anti-join: exclude any RMS row where `case_number` matches the blocklist

**Layer 2 — Type Fallback:**
- Join `IncidentType1/2/3` to `incident_type_map.csv` (maps raw RMS strings to canonical categories)
- Cross-reference with `CallType_Categories.csv` for string harmonization
- Exclude any RMS row where mapped category resolves to DV/domestic dispute
- Catches cases not yet in the DV roster (new incidents, roster lag)

### 6.3 Order of Operations

```
RMS raw data
  → snake_case normalization
  → case_number standardization (regex: ^\d{2}-\d{6}$)
  → Layer 1: anti-join against DV blocklist
  → Layer 2: type fallback exclusion
  → Log exclusion counts by reason (dv_case_match vs type_fallback)
  → Output: RMS_T4_scoring_ready (feeds into Tier 2 and precursor)
```

**The exclusion mask must be applied BEFORE:**
- Tier 2 Part 1 scoring (Section 7.2)
- Precursor correlation (Section 12)
- Any RMS row count used in Data Quality Note

### 6.4 PII Rules

- **NEVER** copy `dv_final_enriched.csv` into the `Acute_Crime/` directory
- The project-local blocklist is `Data/dv_case_numbers_for_t4.csv` (3 columns: `case_number`, `source`, `source_date_end`) — **1,535 rows**, PII-safe (no victim/offender/address/narrative data)
- This file combines 1,322 cases from `dv_final_enriched.csv` + 213 new cases extracted from `2025_10_29_to_2026_04_16_DV_roster.pdf`
- See `dv_doj/docs/pii_policy.md` for full policy

### 6.5 Roster Lag Warning

`backfill_dv` `ValidationConfig` specifies `date_end = 2025-12-31`, but `dv_final_enriched.csv` ends **2025-10-29** (1,322 rows). A supplemental PDF extraction (223 pages, 2025-10-29 to 2026-04-16) added 213 new case numbers. The combined blocklist `Data/dv_case_numbers_for_t4.csv` now covers **1,536 unique case numbers** (2023-01-01 through 2026-04-16). Page 216 (incident 04/11/26, P.O. Andres Lopez 375) had no case number in the text layer — resolved manually as `26-033051`. Before running any T4 analysis window past 2026-04-16:
1. Regenerate the DV roster with an updated `date_end`
2. After loading `dv_final_enriched.csv`, compute `max(IncidentDate)`
3. If `max(IncidentDate)` < `rms_pull_start` → **HALT** and flag: `[DV ROSTER LAG — regenerate backfill_dv before proceeding]`

### 6.6 Data Quality Note Extension

After applying the DV exclusion mask, log to the Data Quality Note:
- Total RMS rows before filter
- Rows excluded by `dv_case_match` (Layer 1)
- Rows excluded by `type_fallback` (Layer 2)
- Final scoring-ready row count

### 6.7 Blind Spots

- **Roster lag:** New DV cases may be missing from blocklist until DV ETL runs; type fallback mitigates but won't catch every edge spelling
- **Over-exclusion:** Type fallback may rarely catch non-DV disputes labeled "domestic" — log for manual review
- **Under-exclusion:** RMS entries with no domestic wording and not on DV roster will remain (intended behavior)
- **Tier 2 impact:** Excluding DV reduces RMS Part 1 at residences; public Part 1 crimes remain
- **CAD side:** Master prompt whitelist focuses on street disorder; parallel CAD domestic filter is out of current scope unless extended

---

## 7. Scoring Model (Section 7)

### 7.1 Tier 1 — CAD Base Points (Citizen-Generated Only)

| Call Category | Points |
|---------------|--------|
| Shots fired / weapons | 5 |
| Aggravated assault (CAD) | 4 |
| Fights / group fights | 3 |
| Disorderly groups | 3 |
| Suspicious persons/vehicles | 2 |
| Ordinance violations | 1 |

### 7.2 Tier 2 — RMS Part 1 Crime Bonus (Added on Top of CAD)

| RMS UCR Part 1 Category | Bonus Points |
|--------------------------|-------------|
| Homicide / Attempted Homicide | +10 |
| Robbery (firearm) | +7 |
| Aggravated Assault (confirmed RMS) | +5 |
| Robbery (other weapon / strong arm) | +5 |
| Burglary | +3 |
| Motor Vehicle Theft | +2 |
| Larceny (threshold: >= $500) | +1 |

**Link rule:** RMS record associates with a scoring location if `FullAddress` (normalized) matches `Block_Final` AND `IncidentDate` falls within the same 28-day cycle.

**DV exclusion applies before Tier 2 scoring.**

### 7.3 Recency Decay Multiplier

| Age of Call (from `analysis_date`) | Multiplier |
|------------------------------------|------------|
| <= 28 days (current cycle) | 1.00 |
| 29-90 days | 0.75 |
| 91-180 days | 0.50 |
| 181+ days (YTD) | 0.25 |

Apply decay to both Tier 1 and Tier 2 scores independently, then sum.

### 7.4 Repeat-Location Boost

If the same canonical location has >= 3 **citizen-generated** scoring incidents in the **current 28-day cycle**, apply **1.25x** location boost to the cycle score.

Configurable: the >= 3 threshold and 1.25x multiplier are defaults. Adjust in `run_parameters` if directed by command.

### 7.5 Final Score Formula

```
location_score = [ Σ(tier1_points × recency_multiplier) + Σ(tier2_bonus × recency_multiplier) ] × location_boost
```

### 7.6 Ranking

- Rank by weighted score, never raw count
- Compute calls-per-street-segment-day as normalizing denominator
- Flag any location whose current-cycle score is > 2 standard deviations above its own 90-day rolling mean as **Emerging** (Section 9)

---

## 8. Call Type Filtering (Sections 5-6)

### 8.1 Whitelist (Focus Call Types)

- Shots fired / weapons-related
- Aggravated assault, simple assault
- Fights / group fights
- Disorderly groups, "Group" calls
- Suspicious persons, suspicious vehicles
- Public drinking, public urination
- Gambling
- Disorderly persons
- City ordinance violations and warnings

### 8.2 Blacklist (Exclusions)

- Medical Call, Medical Call - Oxygen
- Motor Vehicle Crash, Motor Vehicle Impound
- Alarm - Burglar (high false-alarm rate)
- Parking Complaint
- HQ Assignment / Task Assignment / Notification Request
- Assist Other Agency (unless co-located with Part 1 crime at same address)

### 8.3 Disposition Exclusions

- `Unfounded`
- `Canceled`
- `Checked OK`
- `Gone on Arrival` — if GOA pattern persists at same location >= 3 times, retain as low-confidence signal

### 8.4 Self-Initiated Filtering (Critical)

| `HowReported` Value | Treatment |
|---------------------|-----------|
| `Self-Initiated` | EXCLUDE from demand scoring. Move to patrol-presence section. |
| `Radio` | Evaluate context. If dispatched to citizen-originated call (linked `ReportNumberNew` exists in citizen-generated records), INCLUDE. If no linked citizen call, EXCLUDE. |
| `9-1-1`, `Phone`, `Walk-In` | INCLUDE — citizen demand. |

Report `self_init_count` in separate column. Flag if self-initiated volume >= 2x citizen demand at a location (possible patrol-feedback loop).

---

## 9. Location Normalization (Section 4)

Convert each address to:
- **Street segment:** e.g., `"100 Block Main St"`
- **Intersection:** if address contains `"&"`

### Validation Rules

- `Block_Final` must contain both street-number bucket AND street name
- Flag rows where `StreetName` is null, or `Block_Final` begins with `"& "` or `"0 Block "` without street name
- Alphabetize intersection components before grouping (`"Main & 1st"` = `"1st & Main"`)
- Remove trailing `"Hackensack, NJ, 07601"` before grouping

### GIS Enhancements (When Coordinates Available)

- Snap points to street centerlines (NJDOT or local layer)
- Cluster points within 50-100 ft using `GenerateNearTable` or DBSCAN
- Aggregate to street-segment polygons for command briefings

---

## 10. Hotspot Classification (Section 9)

Apply in priority order (first match wins):

| Label | Criteria |
|-------|----------|
| **Chronic** | Top 10% of weighted scores **citywide** for **3+ consecutive 28-day cycles** |
| **Persistent** | Current cycle AND prior cycle scoring list; below Chronic threshold |
| **Emerging** | Current-cycle score >= 2x prior-cycle score, OR > 2 SD above own 90-day rolling mean |
| **Diminishing** | Prior cycle present; current-cycle score dropped > 50% — trigger displacement check |
| **One-off** | Isolated incident(s) in current cycle only; no pattern across prior cycles |

"Top 10% citywide" = percentile rank across ALL scored locations regardless of post. Do not compute per-post.

Chronic locations warrant CPTED review, landlord/business contact, or multi-agency coordination.

---

## 11. Time Analysis (Section 8)

### Fixed Time Bins

| Bin | Hours |
|-----|-------|
| Early Morning | 00:00-03:59 |
| Morning | 04:00-07:59 |
| Morning Peak | 08:00-11:59 |
| Afternoon | 12:00-15:59 |
| Evening Peak | 16:00-19:59 |
| Night | 20:00-23:59 |

### Required Analyses

- Time-of-day distribution per hotspot (use bins, not raw hours in briefing output)
- Day-of-week distribution
- Seasonal comparison (YoY — not raw period-over-period without seasonal control)
- Weekday vs. weekend split

---

## 12. Posts/Districts (Section 10)

| Post | Target Hotspots |
|------|-----------------|
| Post 5 | 2-3 |
| Post 6 | 1 |
| Post 7 | 5-6 |
| Post 8 | 5-6 |
| Post 9 | 3-5 |

Targets are guidelines, not quotas. Do not pad weak locations to fill a target.

---

## 13. Cycle-Aligned Reporting (Section 11)

- **Current 7-day cycle** — e.g., `T4_C01W02`
- **Current 28-day cycle** — e.g., `T4_C01`
- **YTD**

Use **`cycle_id` / cycle labels from Section 0 run parameters** (aligned with command’s `T4_Master.xlsx` scheduling practice). The reporting workbook’s `ReportName` may be only `T4_Current` — do not use it as the pipeline cycle key. Never invent arbitrary date windows. Populate `cycle_7day` and `cycle_28day` from Run Parameters before any output. See [Docs/t4_cycle_id_strategy.md](Docs/t4_cycle_id_strategy.md).

---

## 14. Precursor Correlation (Section 12)

For each scored hotspot:

1. Identify all CAD disorder/group/suspicious calls at that canonical location within the analysis window
2. Check whether any RMS Part 1 crime was recorded at **same canonical address +/- 1 block** within a **14-day forward window** of each CAD call
   - Found within 14 days → **"Precursor Pattern (Primary)"**
   - Found within 15-30 days → **"Precursor Pattern (Extended)"** — lower confidence
3. List the CAD `ReportNumberNew` and matching RMS `CaseNumber` for command drill-down
4. No RMS match → no precursor flag

**Address tolerance:** +/- 1 block accounts for imprecise RMS address entry. Normalize both to `Block_Final` before matching.

**DV-excluded RMS rows must NOT enter the precursor pool.**

---

## 15. Displacement Analysis (Section 14)

**Trigger:** Any location classified **Diminishing**.

1. Identify prior-cycle hotspot centroid
2. Generate 1-3 block (approx 300-900 ft) buffer ring around centroid
3. Query scoring incidents from current cycle inside the ring but outside original hotspot boundary
4. If current-cycle activity inside ring >= 50% of prior-cycle hotspot volume → flag **"Possible Displacement"**
5. Report displacement candidates in citywide summary and relevant post section

Displacement is a hypothesis, not a confirmed finding. Requires supervisor ground-truth validation.

---

## 16. Effectiveness Feedback Loop (Section 18)

At the start of each new 28-day cycle:

1. Pull prior cycle's Top 5 directed patrol locations
2. Compare current-cycle `weighted_score` to prior-cycle score
3. Classify each:
   - Score dropped > 25% → **"Possible Effect"** (correlation only; weather/staffing confound)
   - Score unchanged or increased → **"No Observed Effect"** — escalate to Chronic review or CPTED
   - Location no longer in scoring population → **"Resolved or Displaced"** — check displacement
4. Append 3-5 bullet Effectiveness Note to Citywide Summary

---

## 17. Output Integration Schema (Section 16)

28-field export for Power BI + ArcGIS:

| Field | Type | Notes |
|-------|------|-------|
| `location` | string | Canonical block or intersection |
| `post` | int | 5-9 |
| `pdzone` | string | From CAD or spatial join |
| `grid` | string | |
| `latitude` | float | |
| `longitude` | float | |
| `weighted_score` | float | Post-decay, post-boost |
| `raw_count` | int | Citizen-generated only |
| `self_init_count` | int | Separate column |
| `rms_part1_count` | int | RMS Part 1 hits at location in cycle |
| `risk_level` | string | High / Medium / Low |
| `classification` | string | Chronic / Persistent / Emerging / Diminishing / One-off |
| `top_call_types` | string | Semicolon-separated top 3 |
| `time_pattern` | string | Dominant bin |
| `dow_pattern` | string | Dominant day(s) |
| `trend_pct` | float | Cycle-over-cycle % change |
| `precursor_pattern` | string | None / Primary / Extended |
| `precursor_cases` | string | Semicolon-separated RMS case numbers |
| `displacement_flag` | bool | |
| `displacement_candidate` | string | Nearby location if suspected |
| `confidence` | string | High / Medium / Low |
| `source_reports` | string | Semicolon-separated CAD ReportNumberNew |
| `last_incident_date` | date | |
| `unique_officers` | int | Citizen-generated responses only |
| `cycle_7day` | string | e.g., T4_C01W02 |
| `cycle_28day` | string | e.g., T4_C01 |
| `data_quality_flags` | string | Semicolon-separated flags |

**Formats:** CSV (primary / Power BI), JSON (API), GeoJSON (ArcGIS), Feature Class (File GDB)

---

## 18. Data Quality Checks (Section 17)

Append a Data Quality Note to every output:

| Check | Threshold / Action |
|-------|-------------------|
| Missing location data | > 10% of filtered rows → flag |
| Unmapped call types (not in whitelist or blacklist) | Any → list them |
| Invalid coordinates (outside Hackensack bounding box) | Any → exclude from GIS |
| Duplicate incidents (same `ReportNumberNew`) | Any → deduplicate before scoring |
| `TimeResponse = 0` or `TimeDispatched = TimeOfCall` | Flag as data-entry artifact |
| `TimeSpent = 0` on dispatched calls | Flag |
| `Block_Final` missing street name | Flag |
| Intersection with leading `"& "` | Flag |
| `Disposition = Unfounded/Canceled/Checked OK` rate | Report % per location |
| `HowReported = Radio` with no linked citizen call | Report count — manual review |
| `UCRCode` null on RMS records used for Tier 2 | Flag — derive from IncidentType1 |
| DV exclusion: rows excluded by `dv_case_match` | Report count |
| DV exclusion: rows excluded by `type_fallback` | Report count |
| DV exclusion: total rows before/after filter | Report counts |

---

## 19. Confidence Rating (Section 15.6)

| Condition | Impact |
|-----------|--------|
| >= 5 citizen-generated scoring incidents in current cycle | Base = **High** |
| 3-4 incidents | Base = **Medium** |
| < 3 incidents | Base = **Low** — do not brief as hotspot; appendix only |
| Missing location on > 10% of location's own records | Downgrade one level |
| `Unfounded/Canceled` rate > 30% at location | Downgrade one level |
| No coordinate data | Flag — no ArcGIS output |

---

## 20. GIS Workflow (Section 13)

### Required Techniques

- **Kernel Density** — visualization
- **Hot Spot Analysis (Getis-Ord Gi*)** — statistical significance
- **Emerging Hot Spot Analysis** (Space-Time Cube) — temporal classification
- **Local Moran's I** (Cluster & Outlier Analysis) — high-high clusters, high-low outliers
- **Spatial Join** — `PDZone`/`Grid` assignment when missing
- Date-based filtering using cycle fields from Run Parameters

### Output Layers (ArcGIS Pro)

- Weighted hotspot layer (graduated color by `weighted_score`)
- Classification layer (Chronic/Persistent/Emerging/Diminishing/One-off as categorical)
- Precursor-pattern layer (CAD→RMS linkages, Primary vs. Extended color-coded)
- Displacement check layer (prior-cycle Diminishing + 3-block radius ring)

### ArcGIS Online Publishing

1. Export final scored feature class to File GDB (`T4_Hotspots_[cycle_id].gdb`)
2. Publish weighted hotspot layer as Hosted Feature Layer (overwrite if cycle exists)
3. Update T4 Dashboard web map with new hosted layer
4. Share with HPD Analytics group only — not public

### Symbology

- Graduated color by `weighted_score` (5-class natural breaks or manual thresholds — document which in Data Quality Note)
- Labels for top 10 locations
- Post boundaries as reference layer

---

## 21. Blind Spots and Pitfalls (Section 20)

Flag in every output:

1. **Reporting bias** — high-volume locations may reflect vigilant callers, not highest actual risk
2. **Over-reliance on call volume** — a quiet location with 2 shots fired outranks 20 disorderly calls; Tier 2 corrects for this
3. **Displacement blindness** — if a hotspot cooled, run displacement check before concluding it resolved
4. **Radio call contamination** — if Radio entries not resolved per Section 6.3, self-initiated can inflate demand
5. **Officer discretion feedback loop** — self-initiated filter mitigates; flag if self-initiated >= 2x citizen demand
6. **Weather/seasonality confounds** — always compare YoY
7. **Small-n instability** — locations with < 3 scoring incidents are Low confidence; do not brief as hotspots
8. **Disposition quality** — high Unfounded/Canceled rate may indicate ghost-caller or data-entry errors
9. **RMS Tier 2 double-counting** — if single incident has both CAD call and RMS record at same location/date, sum Tier 1 + Tier 2 once per record, not twice

---

## 22. Pre-Flight Checklist (Section 22)

Run before every analysis:

- [ ] Section 0 Run Parameters fully populated (`cycle_id`, pull dates, `analysis_date`)
- [ ] CAD pull covers full reporting window (no gaps at cycle boundaries)
- [ ] RMS pull covers same window + 14-day forward buffer for precursor check
- [ ] DV roster covers the analysis window (`max(IncidentDate)` >= `rms_pull_start`)
- [ ] DV exclusion applied before Tier 2 and precursor
- [ ] Call-type whitelist/blacklist applied
- [ ] `HowReported = Radio` entries resolved per Section 6.3
- [ ] Self-initiated separated from citizen-generated demand
- [ ] Disposition exclusions applied (`Unfounded`, `Canceled`, `Checked OK`)
- [ ] Address normalization validated (no `"& "` or `"0 Block "` errors)
- [ ] Intersection alphabetization applied
- [ ] Tier 1 + Tier 2 scoring computed; no double-counting on linked records
- [ ] Recency decay applied to both tiers
- [ ] Cycle fields (`ReportName`, 7-day, 28-day) joined from T4 Master workbook (`T4_Master_Reporting_Template.xlsx`)
- [ ] Prior-cycle Diminishing locations identified; displacement check queued
- [ ] Effectiveness feedback note drafted
- [ ] Confidence ratings applied algorithmically
- [ ] Data Quality Note generated (including DV exclusion counts)
- [ ] Output schema matches Section 16 (28 fields)
- [ ] `cycle_id` is non-null on all output rows

---

## 23. Pending TODOs

All implementation work is tracked here. Do not mark any TODO complete until code is written, tested, and Data Quality Note confirms expected exclusion counts.

| # | ID | Description | Status | Blocking? |
|---|----|-------------|--------|-----------|
| 1 | `confirm-rms-source` | Decide canonical RMS input path (`Acute_Crime/Data` vs AGOL/GDB) and post-snake_case column names | **Pending** | Yes |
| 2 | `blocklist-pipeline` | Implement `case_number` standardization + anti-join to DV blocklist | **Pending** | Yes |
| 3 | `type-fallback` | Join `IncidentType1/2/3` to `incident_type_map`; define DV include/exclude category list | **Pending** | Yes |
| 4 | `score-integration` | Apply exclusion before Tier 2 and precursor; extend Data Quality Note with counts by reason | **Pending** | Yes |
| 5 | `refresh-governance` | Document DV roster refresh cadence; align `backfill_dv` `ValidationConfig` `date_end` with T4 windows | **Pending** | Yes |
| 6 | `cad-rms-qc-preflight` | (Optional) Run `cad_rms_data_quality` validators on T4-window exports | **Pending** | No |

---

## 24. Known Data Issues

- `Data/rms/monthly/2026_02_RMS.xlsx` — **re-exported 2026-04-16** (was 0-byte placeholder); **verified ~539 KB** — [Docs/data_gaps.md](Docs/data_gaps.md)
- `Data/nibrs/` is empty
- DV roster ends 2025-12-31 — regenerate before 2026 runs
- **T4 Master workbook** — inspected 2026-04-16. `ReportName` column contains only `T4_Current`, not structured `T4_C01W02` cycle IDs. Cycle ID generation must be built into pipeline code or sourced from a separate cycle calendar. See §4a for full sheet/column inventory.
- **DV roster actual end date** — `dv_final_enriched.csv` data ends **2025-10-29** (not 2025-12-31 as `ValidationConfig` implies). Gap is ~6 months to present. Regenerate `backfill_dv` before any T4 run.
- **T4 Master column names use spaces** — `How Reported`, `Time of Call`, etc. — not the camelCase in the master prompt. Snake_case normalization must handle both.

---

## 25. Design Constraints

Do not alter the following without explicit instruction from the operator (R. A. Carucci or delegated analyst per Section 0):

- Scoring weights (Tier 1 point values, Tier 2 bonus values)
- Recency decay multipliers (1.00, 0.75, 0.50, 0.25)
- Classification thresholds (Top 10%, 3+ cycles, 2x/2SD, 50% drop)
- Repeat-location boost (>= 3 incidents, 1.25x)
- DV exclusion strategy (blocklist + type fallback, applied before scoring)
- Ethical constraints (Section 21 — non-negotiable)
- Precursor correlation windows (14-day primary, 30-day extended)
- Displacement buffer (1-3 blocks, >= 50% volume threshold)

---

## Claude Code Rules

### Input Validation

- Always validate input paths before reading. Use `os.path.exists()` at the top of every script.
- If a required file is missing, halt and log. Do not substitute dummy data.
- Use `list_directory` or `Glob` to confirm expected files exist at configured paths before pipeline runs.

### PII Protection

- Never write PII-containing files to `Acute_Crime/`.
- If a write target resolves to the `Acute_Crime/` directory and the source contains DV case data beyond `case_number`, abort and raise a warning.
- Any reference to `dv_final_enriched.csv` in code or documentation must include the PII caveat.

### DV Exclusion Enforcement

- Run DV exclusion before any scoring step. The exclusion mask (`dv_case_match` OR `type_fallback`) must be applied and logged before Tier 1 totals are computed and before precursor check.
- Log exclusion counts by reason: row count before filter, rows excluded by `dv_case_match`, rows excluded by `type_fallback`, final scoring-ready row count.
- Check DV roster date range on every run. After loading `dv_final_enriched.csv`, compute `max(IncidentDate)`. If before `rms_pull_start`, halt and flag: `[DV ROSTER LAG — regenerate backfill_dv before proceeding]`.

### Output Integrity

- All outputs must include `cycle_id`. Before writing any output CSV or feature class, assert `cycle_id` is populated from **Section 0 run parameters** (not from reporting workbook `ReportName` unless org later syncs them). If null, halt.
- Output schema must match the 28-field specification in Section 17 of this document.

### Design Preservation

- Preserve all Cursor plan decisions. Do not alter scoring weights, decay multipliers, classification thresholds, or DV exclusion strategy without explicit operator instruction.
- When modifying existing scripts, prefer `Edit` over full rewrites.

### Recommended Claude Code Skills

**Core execution:**
- `python` — All ETL scripts, DV blocklist pipeline, scoring logic, data quality checks
- `bash` — Path validation, directory scaffolding, OneDrive sync verification

**File and data handling:**
- `Read` — Ingest `.csv`, `.md`, `.xlsx`, `.json`, `.txt` from OneDrive paths
- `Write` — Generate output files; must respect PII rules
- `Glob` — Validate expected input files exist before pipeline runs
- `Grep` — Scan for column name variants (`Case Number` vs `CaseNumber`) across exports

**Project management:**
- Use tasks to track the 6 pending TODOs during implementation sessions
- Use `WebSearch` only for NJ AG Directive lookups, ArcPy/AGOL API docs, or Python library references

---

*End of CLAUDE.md — T4 Hotspot Analysis*
