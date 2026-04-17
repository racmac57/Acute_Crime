# ArcGIS Pro Phase 1 Style-Transfer Plan (dv_doj -> operational map)

## Objective

Deliver practical style parity quickly by transferring:

- symbology renderer
- label settings (show/hide, class expression, class SQL)
- definition query text

From source project:
`C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Imported_from_sandbox\dv_doj_arcgis_exports\dv_incidents_arcgis_ready\dv_doj\dv_doj.aprx`

## Policy Decisions Enforced

- Tiered patrol thresholds:
  - Tier A: high confidence + risk >= 0.70
  - Tier B: high/medium confidence + risk 0.55-0.69
  - Tier C: watchlist only
- Downtrend downgrade is not automatic; requires:
  - 2 consecutive down cycles, and
  - supervisor field validation
- ArcGIS overlay scope: top 50 locations
- Confidence calibration starts next cycle with supervisor outcomes

## Chosen Layers (Final Run)

Source styles (from `dv_doj.aprx`):

1. `Statistically Significant Hot Spots`
2. `Priority Intervention Zones (95%+ Confidence)`
3. `Community-Reported Domestic Violence Incidents`
4. `Domestic Violence Incidents (2023 - 2025)`

Target operational layers (in `T4_2026_ArcGIS` map):

1. `DV_Hotspot_Analysis` (renamed in pane to `T4 Persistent Hotspots (Top 50)`)
2. `DV_Intervention_Zones_95pct_Polygons` (renamed to `T4 Priority Intervention Zones (95%+)`)
3. `DV_Incidents_Exclude_HPD_HQ` (renamed to `T4 Community-Reported Incidents`)
4. `DV_Incidents_Within_City` (renamed to `T4 Incidents Within City (Reference)`)

## Workflow

Phase 1 (read-only extraction, immediate value):

1. Run style extraction script (`export_layer_styles.py`) against `dv_doj.aprx` without saving source.
2. Review `Scripts/t4/arcgis/styles/inventory.json`.
3. Select final 2-5 operational style references from exported `.lyrx` files.

Phase 2 (apply + validate):

1. Update `LAYER_MAPPING` and target constants in `apply_layer_styles.py`.
2. Run style apply script.
3. Run validation script (`validate_layer_styles.py`).
4. Complete operator checklist.

Final execution note:

- Apply/validate run against `CURRENT` project context (ArcGIS Pro live session), which is the reliable target context in this environment.

## Runtime Notes

- Read-first, write-second approach is followed.
- Source APRX/GDB are treated as read-only.
- No raw exports are modified.
- If ArcGIS runtime is unavailable in current session, scripts are still production-ready for `propy` execution.

## Transfer Scope vs Deferred

Transferred:

- `.lyrx` style references exported from source layer definitions
- inventory metadata (map, layout, labels, definition query, data source)
- Symbology, labels, and definition queries transferred to all 4 target operational layers
- Content-pane layer names normalized to T4 operational naming

Deferred / Caveats:

- popup configuration
- field aliases
- advanced map layout elements (legends, annotation, map frames)
- service publishing settings
- Direct `.lyrx`-based apply remains unreliable in this environment (`ERROR 000229`); source-layer fallback is the approved operational path

## Script Outputs

Under `Scripts/t4/arcgis/styles/`:

- `inventory.json`
- `export_summary.json`
- `*.lyrx`

Under `_overnight/arcgis_style_transfer/`:

- `style_apply_summary.json`
- `style_validation_report.json`
- `style_validation_report.md`

Latest verification outcome:

- Validation result: **4/4 PASS** in `style_validation_report.md` (source-APRX fallback-aware validation)

## Execution Commands

ArcGIS Pro `propy` commands:

```powershell
"C:\Program Files\ArcGIS\Pro\bin\Python\scripts\propy.bat" "C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\export_layer_styles.py"
"C:\Program Files\ArcGIS\Pro\bin\Python\scripts\propy.bat" "C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\apply_layer_styles.py"
"C:\Program Files\ArcGIS\Pro\bin\Python\scripts\propy.bat" "C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\validate_layer_styles.py"
```

Monthly single-run SOP command (recommended):

```powershell
"C:\Program Files\ArcGIS\Pro\bin\Python\scripts\propy.bat" "C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\run_monthly_style_sop.py"
```

ArcGIS Pro Python window (`exec`) option:

```python
exec(open(r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\export_layer_styles.py").read())
exec(open(r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\apply_layer_styles.py").read())
exec(open(r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\validate_layer_styles.py").read())
```

ArcGIS Pro Python window monthly single-run option:

```python
exec(open(r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Scripts\t4\arcgis\run_monthly_style_sop.py").read())
```

## Monthly SOP Pass/Fail Artifacts

Single-run monthly output files:

- `_overnight/arcgis_style_transfer/monthly_sop_run_report.json`
- `_overnight/arcgis_style_transfer/monthly_sop_run_report.md`

Pass criteria:

- `overall_status == "pass"` in `monthly_sop_run_report.json`
- Step status `pass` for:
  - `export_layer_styles`
  - `apply_layer_styles`
  - `validate_layer_styles`
- Output checks all `pass`:
  - export summary check
  - apply summary check
  - validation summary check

## Assumptions / Known Blockers

- Assumes ArcGIS Pro runtime with `arcpy` is available on operator machine.
- Target map for execution is `T4_2026_ArcGIS` in the active `CURRENT` ArcGIS Pro session.
- `.lyrx` files exported from the source project are currently stub-like and not directly loadable by ArcPy (`ERROR 000229`); scripts now use source APRX fallback to maintain operational continuity.
- If layer names drift in future cycles, update `LAYER_MAPPING` candidate names in apply/validate scripts.
