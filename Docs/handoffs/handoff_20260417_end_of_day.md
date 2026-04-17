# Project handoff — Acute_Crime T4 (end of day 2026-04-17)

## Project

**Hackensack PD T4 Hotspot Analysis** (`10_Projects/Acute_Crime`): DV blocklist + type fallback, `Scripts/t4/score_integration`, Data Quality JSON, deliverable HTML/CSV for top hotspot locations.

## Branch / remote

- **`main`** tracking **`origin/main`**. Recent notable commits include T4 pipeline fixes, deliverables (`Docs/deliverables/T4_*`), `export_top5_hotspots_html.py`, gitignore for `Imported_from_sandbox/`, `Docs/imported_sandbox_arcgis_note.md`.

## Completed / current capability

- **`score_integration`**: DV exclusion before Tier 2; NIBRS token parse; decay `float64`; E2E run produces `Output/<cycle_id>/` (folder gitignored).
- **Top 5 citywide**: `Docs/deliverables/T4_C01W02_top5_hotspots_*` (HTML + ArcGIS CSV + meta); regenerator `Scripts/t4/export_top5_hotspots_html.py`.
- **Sandbox ArcGIS mirror** (local only): `Imported_from_sandbox/dv_doj_arcgis_exports/` (~39 MB) — **gitignored**; see `Docs/imported_sandbox_arcgis_note.md`.
- **CAD exports reviewed**: Monthly 2026_01–03 disposition ~0.1–0.2% empty; **yearly** `2024_CAD_ALL` ~**6%** empty disposition vs **2025** ~0.15% — flag for any disposition-based scoring on 2024.
- **Policy discussion (not implemented)**: CAD **Tier 1** currently ignores **disposition**; SME consensus wanted to **down-weight** GOA / Unfounded / Checked OK etc.; **`cad_rms_data_quality`** / `DispositionValidator` + `enhanced_esri_output_generator` mapping is the right upstream integration point; **Sandbox** `CAD_Data_Cleaning_Engine` is the fuller historical codebase vs thin OneDrive copy.

## Open / next

| Item | Notes |
|------|--------|
| **CAD disposition → Tier 1 weighting** | Design pass; normalize via existing validator mapping; DQ note. |
| **Block_Final + Radio §6.3** | Still gaps per `CHANGELOG`. |
| **`score_integration` PATHS** | Hardcoded OneDrive project root — add CLI overrides if needed on other PCs. |
| **CAD_Data_Cleaning_Engine** | See **Claude Code prompt** below — sync Sandbox → OneDrive for laptop parity. |

---

## Opening prompt for tomorrow (paste into Cursor / Claude)

```
Read first — do not re-summarize the master prompt unless needed:
- Docs/handoffs/session_state.json
- Docs/handoffs/handoff_20260417_end_of_day.md

Context: Acute_Crime T4 — score_integration with DV blocklist + type fallback; top-5 deliverables in Docs/deliverables; CAD disposition is present on monthly/yearly exports but NOT used in scoring yet (policy TBD). cad_rms_data_quality DispositionValidator is the alignment point with enhanced_esri_output_generator.

Goal today: [pick one] (1) Implement disposition multiplier stub for CAD Tier 1 behind a flag, OR (2) run /validate-monthly on latest CAD+RMS for T4 window, OR (3) execute CAD_Data_Cleaning_Engine Sandbox→OneDrive sync per handoff Claude Code prompt.

Constraints: PII-safe blocklist only; no dv_final_enriched in repo; Output/ gitignored — regenerate artifacts locally if needed.
```

---

## Prompt for Claude Code — investigate & optional Sandbox → OneDrive sync

**Copy everything between the lines into Claude Code.**

```
You are working on a Windows OneDrive layout for Hackensack PD ETL.

### Scope
1. Read all files under:
   C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Docs\handoffs\
   Summarize resume context for the Acute_Crime T4 project (no verbatim duplication of master prompt).

2. Compare two directories:
   SOURCE (full historical CAD cleaning framework):
   C:\_Sandbox\02_ETL_Scripts\CAD_Data_Cleaning_Engine
   TARGET (thin / partial mirror on OneDrive — may be stale):
   C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine

3. Produce a concise report:
   - File/folder count delta (or representative: processors/, validators/, scripts/, config/, doc/)
   - Whether TARGET is safe to overwrite wholesale or needs three-way merge
   - Presence of .git, large data/, xlsx in-repo — recommend exclude patterns for robocopy
   - Risk list: OneDrive sync conflicts, path hardcoding to Sandbox, duplicate enhanced_esri_output_generator if both differ

4. Recommendation: Is mirroring SOURCE → TARGET worth doing?
   - YES if: laptop must edit/run the same pipeline; single canonical tree desired; TARGET is clearly incomplete.
   - NO /defer if: TARGET is intentionally minimal; full copy would bloat OneDrive; better to use git remote from one machine only.

5. If merge is warranted, draft a single robocopy or PowerShell recipe (with /XD for __pycache__, .git optional, large binary folders) and a verification step (dir diff or python -c import smoke test). Do not run destructive deletes without explicit user confirmation.

Deliver: report + recommended next command only (no bulk file write unless user confirms).
```

---

## Is Sandbox → OneDrive sync “worth doing”?

| Worth it | Caveats |
|----------|---------|
| **Yes**, if the **laptop** must run the **same** validation/cleaning scripts as the desktop and **Target OneDrive** is currently **only** `enhanced_esri_output_generator.py`-scale — you already confirmed Sandbox has the **full** engine (README, `processors/`, parallel validators, ESRI rebuild story). | Use **inventory-first** (diff tree sizes, `.git` boundaries). Prefer **`robocopy /E` with excludes** over blind overwrite. If Sandbox has **huge `data/`**, mirror **code + docs** first, link large binaries separately. **OneDrive** can churn on big folders — sync off-hours. |

**Bottom line:** **Yes for code + docs parity** across machines; **careful for data artifacts and git repos** — either copy the **whole git repo** to OneDrive or one **clean export** without nested `.git` conflicts.

---

## Files touched this handoff

- `Docs/handoffs/handoff_20260417_end_of_day.md` (this file)
- `Docs/handoffs/session_state.json` (updated)
