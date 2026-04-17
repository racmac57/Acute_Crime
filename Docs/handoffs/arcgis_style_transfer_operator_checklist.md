# ArcGIS Style Transfer Operator Checklist (Phase 1)

## Before You Run

- [ ] ArcGIS Pro installed and `propy` available
- [ ] Source APRX exists:
  - `C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Imported_from_sandbox\dv_doj_arcgis_exports\dv_incidents_arcgis_ready\dv_doj\dv_doj.aprx`
- [ ] Confirm source is treated read-only (no manual edits in this workflow)
- [ ] Confirm top-50 hotspot policy is active for overlay layer scope

## Policy Guardrails (must hold)

- [ ] Tier A = high confidence + risk >= 0.70
- [ ] Tier B = high/medium confidence + risk 0.55-0.69
- [ ] Tier C = watchlist only
- [ ] No automatic downgrade on one-cycle downtrend
- [ ] Downgrade only after 2 consecutive down cycles + supervisor validation
- [ ] Confidence calibration is deferred to next cycle with supervisor outcomes

## Step 1 — Inventory + Export Styles

- [ ] Run `export_layer_styles.py`
- [ ] Capture source APRX modified time before run
- [ ] Open `Scripts/t4/arcgis/styles/inventory.json`
- [ ] Verify chosen layer names exist:
  - `T4_Persistent_Hotspots_Top50`
  - `Patrol_Posts`
  - `PD_Zones`
  - `Patrol_Grid`
  - `City_Boundary`
- [ ] Open `Scripts/t4/arcgis/styles/export_summary.json`
- [ ] Confirm exported `.lyrx` count > 0
- [ ] Confirm source APRX modified time is unchanged after run
- [ ] Confirm inventory contains at least one map and one layout
- [ ] Confirm no `error` entries in inventory for critical layers
- [ ] Confirm `.lyrx` file count matches non-skipped, non-error inventory layer entries

## Step 2 — Apply Styles

- [ ] Set `TARGET_APRX` and `TARGET_MAP_NAME` in `apply_layer_styles.py`
- [ ] Run `apply_layer_styles.py`
- [ ] Open `_overnight/arcgis_style_transfer/style_apply_summary.json`
- [ ] Confirm each mapped layer status is `applied` or explicitly documented skipped

## Step 3 — Validate Parity

- [ ] Run `validate_layer_styles.py`
- [ ] Open `_overnight/arcgis_style_transfer/style_validation_report.md`
- [ ] For each layer, verify:
  - [ ] renderer type matches
  - [ ] class break count/labels/upper bounds match (if class breaks renderer)
  - [ ] definition query text matches
  - [ ] label expression + SQL + visibility match

## Monthly SOP Single-Run (preferred)

- [ ] Run `run_monthly_style_sop.py`
- [ ] Open `_overnight/arcgis_style_transfer/monthly_sop_run_report.md`
- [ ] Confirm overall status is **PASS**
- [ ] Confirm step status is `pass` for:
  - [ ] `export_layer_styles`
  - [ ] `apply_layer_styles`
  - [ ] `validate_layer_styles`
- [ ] Confirm output checks are all `pass`:
  - [ ] export summary check
  - [ ] apply summary check
  - [ ] validation summary check

## Manual Visual QA (ArcGIS Pro)

- [ ] Open target map and verify symbol colors/sizes are operationally readable
- [ ] Toggle labels on/off and verify clutter is acceptable at operational zoom levels
- [ ] Verify top-50 hotspots are not hidden by definition query mismatch
- [ ] Verify zone/post/grid overlays align with hotspot points
- [ ] Round-trip test: add one exported `.lyrx` to blank map and confirm symbology/labels preview
- [ ] Confirm no raw `DV_*` duplicate layer is visible when corresponding `T4 ...` layer exists
- [ ] Confirm intervention zone circle fills are visibly transparent enough for basemap context
- [ ] Confirm 95% red intervention ring/symbol is clearly visible at command zoom

## Deferred (intentional, not a defect)

- [ ] popup formatting
- [ ] field aliases
- [ ] layout and print products
- [ ] publishing/service item settings

## Signoff

- [ ] Date/time:
- [ ] Operator:
- [ ] Result: PASS / PASS-WITH-DEFERRALS / BLOCKED
- [ ] Notes:

## Git Hygiene

- [ ] `git status` shows new style artifacts only under `Scripts/t4/arcgis/styles/`
- [ ] No modifications under source export folders or raw data exports

## Completed Run Notes (2026-04-17)

- [x] Source inventory/export executed successfully.
- [x] Target map execution context set to `CURRENT` (`T4_2026_ArcGIS`).
- [x] Target layers loaded and mapped:
  - `DV_Hotspot_Analysis`
  - `DV_Intervention_Zones_95pct_Polygons`
  - `DV_Incidents_Exclude_HPD_HQ`
  - `DV_Incidents_Within_City`
- [x] Content-pane names normalized to operational T4 naming.
- [x] Validation report outcome: **4/4 PASS**.

### Known caveat carried forward

- Exported `.lyrx` files from this source run are not directly loadable in this environment (`ERROR 000229`).
- Operational style transfer succeeded using source-APRX fallback logic in `apply_layer_styles.py`.
- Keep this fallback path as the approved method unless `.lyrx` export reliability is remediated in a future cycle.

## Next Cycle (3-line SOP)

1. Load/update target operational layers in `T4_2026_ArcGIS`, then run `run_monthly_style_sop.py`.
2. Confirm `_overnight/arcgis_style_transfer/monthly_sop_run_report.md` shows overall **PASS**.
3. Confirm content-pane names remain T4 operational labels and record any new caveats in this checklist before handoff.
