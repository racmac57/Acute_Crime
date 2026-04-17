# T4 config defaults & column aliases (copy-paste artifacts)

*Plan mode cannot create `.yaml` / `.py` in this repo session — save the blocks below into `config/t4_defaults.yaml` and `Scripts/t4/column_aliases.py` when using Agent mode or locally.*

---

## 1. `confirm-rms-source` — closed default

**Decision:** **Default RMS input = local** monthly/yearly XLSX under `Acute_Crime/Data/rms/`. Use **AGOL / hosted CFS** only when the run must match the published dashboard layer exactly (`rms_input_mode: agol_feature_layer`). Document the choice in the Data Quality Note per run.

---

## 2. `config/t4_defaults.yaml` (create at project root)

```yaml
# T4 pipeline defaults — paths and source mode
rms_input_mode: local_xlsx  # local_xlsx | agol_feature_layer

paths:
  project_root: "C:/Users/carucci_r/OneDrive - City of Hackensack/10_Projects/Acute_Crime"
  rms_monthly: "{project_root}/Data/rms/monthly"
  rms_yearly: "{project_root}/Data/rms/yearly"
  cad_monthly: "{project_root}/Data/cad/monthly"
  cad_yearly: "{project_root}/Data/cad/yearly"
  dv_case_blocklist: "{project_root}/Data/dv_case_numbers_for_t4.csv"

external:
  incident_type_map: "C:/Users/carucci_r/OneDrive - City of Hackensack/02_ETL_Scripts/dv_doj/docs/mappings/incident_type_map.csv"
  standards_nibrs_map: "C:/Users/carucci_r/OneDrive - City of Hackensack/09_Reference/Standards/NIBRS/DataDictionary/current/mappings/rms_to_nibrs_offense_map.json"
  standards_ucr_schema: "C:/Users/carucci_r/OneDrive - City of Hackensack/09_Reference/Standards/NIBRS/DataDictionary/current/schema/ucr_offense_classification.json"

agol:
  cfs_service_note: "See CLAUDE.md §3 for hosted Calls For Service URL when using AGOL mode."
```

---

## 3. Workbook typo: `HourMinuetsCalc` — closed for build

**Source column:** `HourMinuetsCalc` (misspelled *Minuets* in Excel).

**Canonical snake_case after normalization:** `hour_minuets_calc` (keeps traceability to source spelling) **or** `hour_minutes_calc` if you prefer corrected English — pick one and use consistently in code.

**Alias map (lowercase keys for matching):**

| Raw / variant | Canonical snake |
|---------------|-----------------|
| `HourMinuetsCalc` | `hour_minuets_calc` |
| `hourminuetscalc` | `hour_minuets_calc` |
| `hour minuets calc` | `hour_minuets_calc` |

Apply the same pattern for other spaced headers from §4a (`How Reported` → `how_reported`, etc.).

---

## 4. Related docs

- [t4_cycle_id_strategy.md](t4_cycle_id_strategy.md)
- [data_gaps.md](data_gaps.md)
- [plans/t4_rms_dv_filtering_d5a59b9b.plan.md](plans/t4_rms_dv_filtering_d5a59b9b.plan.md)
