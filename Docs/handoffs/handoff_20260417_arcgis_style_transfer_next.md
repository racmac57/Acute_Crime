# Project handoff — Acute_Crime ArcGIS style transfer + approved policy decisions

## Why this handoff exists

The Persistent Hotspots MVP+ package is delivered, reviewed, committed, and pushed.
Next work is ArcGIS operationalization and confidence-calibration setup, using a fresh context window.

## Current known-good state

- Persistent hotspot deliverables are published in `Docs/deliverables/`:
  - `T4_persistent_hotspots_citywide.csv`
  - `T4_persistent_hotspots_command_staff.md`
  - `T4_persistent_hotspots_technical_appendix.md`
- Repro script exists: `Scripts/t4/persistent_hotspots.py`
- ArcGIS source project path provided by user:
  - `C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Imported_from_sandbox\dv_doj_arcgis_exports\dv_incidents_arcgis_ready\dv_doj\dv_doj.aprx`
- ArcGIS folder inventory confirms:
  - `dv_doj.aprx`
  - `dv_doj.gdb`
  - no existing exported `.lyrx` style library in that folder

## Approved command decisions (locked)

1. **Patrol threshold policy:** Tiered (Decision D)
   - Tier A: high confidence + risk >= 0.70 (mandatory patrol windows)
   - Tier B: high/medium confidence + risk 0.55-0.69 (discretionary/surge)
   - Tier C: watchlist only
2. **Downtrend downgrade policy:** balanced
   - require 2 consecutive down cycles + supervisor field validation
3. **ArcGIS overlay scope:** top 50 operational set
4. **Confidence calibration trigger:** next cycle + supervisor outcomes

## Next implementation objective

Create a practical Phase 1 ArcGIS style-transfer workflow that is good enough for operations now:
- focus on **2-5 key layers**
- transfer **symbology + labeling + definition queries**
- skip popups/aliases for this pass
- include validation steps

---

## Opening prompt for fresh Claude Code context (copy/paste)

```text
Read first:
- Docs/handoffs/session_state.json
- Docs/handoffs/handoff_20260417_persistent_hotspots_mvp_plus.md
- Docs/handoffs/handoff_20260417_arcgis_style_transfer_next.md

Context:
Acute_Crime Persistent Hotspots MVP+ is complete and pushed. We now need an ArcGIS Pro Phase 1 style-transfer workflow from dv_doj.aprx into the current operational map setup.

Source ArcGIS project:
C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Imported_from_sandbox\dv_doj_arcgis_exports\dv_incidents_arcgis_ready\dv_doj\dv_doj.aprx

Goal:
Produce a practical ArcPy workflow for style parity under time constraints:
1) inventory maps/layers in dv_doj.aprx (read-only)
2) pick 2-5 key operational layers
3) export style references (.lyrx) for those layers
4) generate ArcPy apply script to transfer symbology + labels + definition queries to target layers
5) generate validation script/checklist (renderer type, class breaks, label expression, query text)

Approved policy decisions to enforce in docs/output:
- Tiered patrol thresholds:
  Tier A high + risk>=0.70, Tier B high/medium 0.55-0.69, Tier C watchlist
- Downtrend downgrade needs 2 consecutive down cycles + supervisor field validation
- ArcGIS overlay scope now = top 50 locations
- Confidence calibration starts next cycle with supervisor outcomes

Constraints:
- Read-first, write-second
- No destructive edits to source aprx/gdb
- Do not modify raw exports
- Keep output operational (good enough now, not perfect)
- If blocked by ArcGIS runtime/environment access, still deliver scripts + checklist + assumptions and mark runtime step clearly

Deliverables:
- Docs/handoffs/arcgis_style_transfer_plan.md
- Scripts/t4/arcgis/export_layer_styles.py
- Scripts/t4/arcgis/apply_layer_styles.py
- Scripts/t4/arcgis/validate_layer_styles.py
- Docs/handoffs/arcgis_style_transfer_operator_checklist.md

At end, report:
- chosen 2-5 layers
- what was transferred vs deferred
- exact run commands
- blockers/assumptions
```

---

## Operator note

If ArcGIS Pro is already open with `dv_doj.aprx`, keep it open for visual confirmation after script generation.
If runtime automation is not available in-session, run the generated scripts in ArcGIS Pro Python (`propy`) and validate with the checklist.

