# T4 ArcGIS data paths & `C:\TEMP` → OneDrive mirror

**Purpose:** Document why `T4_2026_ArcGIS.aprx` layers break across machines, how to audit/repair sources in ArcGIS Pro, and how the **`C:\TEMP`** → **OneDrive `\TEMP`** robocopy mirror is automated.

**Last updated:** 2026-04-19

---

## 1. Canonical locations (this project)

| Item | Path |
|------|------|
| ArcGIS Pro project | `10_Projects\Acute_Crime\T4_2026_ArcGIS\T4_2026_ArcGIS\T4_2026_ArcGIS.aprx` |
| Automation scripts | `10_Projects\Acute_Crime\T4_2026_ArcGIS\automation\` |
| ArcPy audit / repair helpers | `10_Projects\Acute_Crime\T4_2026_ArcGIS\scripts\` |
| Existing T4 ArcPy SOP scripts | `Scripts/t4/arcgis/` (e.g. `reconnect_layers.py`, style SOP) |

---

## 2. Desktop vs laptop: why layers show broken (`!`)

Operational map layers were authored against a **file geodatabase** under **`C:\TEMP\DV_Analysis\dv_doj.gdb`**. That path exists on the analysis workstation; another PC (e.g. laptop) will not resolve **`C:\TEMP\...`** unless the same tree exists locally or you **repair data sources** in the `.aprx`.

**Esri reference:** [Updating and fixing data sources](https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/updatingandfixingdatasources.htm) (ArcGIS Pro `arcpy.mp`, `updateConnectionProperties`).

**Mitigations (pick one or combine):**

1. **Mirror `C:\TEMP` into OneDrive `\TEMP`** (see §4) so the laptop has  
   `{OneDrive}\TEMP\DV_Analysis\dv_doj.gdb\...`, then use **`repair_aprx_data_sources.py`** (or `Scripts/t4/arcgis/reconnect_layers.py`) to repoint from `C:\TEMP\...` to the OneDrive path.
2. **Project → Options → Current settings:** enable **Store relative pathnames to data sources** and keep the GDB under the same folder tree as the `.aprx`.
3. **Package Project** (`.ppkx`) if you need a fully self-contained handoff.

---

## 3. Audit & repair (ArcGIS Pro, `arcgispro-py3`)

Scripts live in **`T4_2026_ArcGIS/scripts/`**:

| Script | Role |
|--------|------|
| `audit_aprx_data_sources.py` | Walks maps/layers/tables; writes `datasource_manifest.json` next to the `.aprx` (or path you pass). |
| `repair_aprx_data_sources.py` | Applies `PATH_REPLACEMENTS` via `ArcGISProject.updateConnectionProperties`; saves `T4_2026_ArcGIS_repaired.aprx` by default. |

**Python window:** Pasting a script does **not** define `__file__`. Both scripts use a **`T4_ROOT_FALLBACK`** under this repo; edit it if your clone path differs, or run the script with **Run Script** / `propy.bat` so `__file__` resolves.

**Repair config:** In `repair_aprx_data_sources.py`, set pairs such as:

- From: `C:\TEMP\DV_Analysis\dv_doj.gdb`
- To: `C:\Users\carucci_r\OneDrive - City of Hackensack\TEMP\DV_Analysis\dv_doj.gdb`  
  (adjust for the machine that opens the project.)

---

## 4. `C:\TEMP` → OneDrive `\TEMP` mirror (robocopy)

**Goal:** Keep **`%USERPROFILE%\OneDrive - City of Hackensack\TEMP`** identical to **`C:\TEMP`** so DV/GIS outputs under `TEMP\DV_Analysis\` exist on the synced drive for the laptop.

**Scripts (`T4_2026_ArcGIS/automation/`):**

| File | Role |
|------|------|
| `mirror_c_temp_to_onedrive.ps1` | `robocopy /MIR` with logging under `...\TEMP\.mirror_logs\`. Use `-ListOnly` for a dry run. |
| `run_mirror_c_temp_to_onedrive_now.bat` | Same mirror; convenient double-click / `cmd` run. |
| `Register-CtempMirrorScheduledTask.ps1` | Registers Windows task **`Mirror_C_TEMP_to_OneDrive_TEMP`** (default **every 60 minutes**). |

**Run the scheduled-task registration** (from PowerShell, same folder):

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\Register-CtempMirrorScheduledTask.ps1
```

Verify:

```powershell
Get-ScheduledTask -TaskName 'Mirror_C_TEMP_to_OneDrive_TEMP' | Format-List TaskName, State, TaskPath
```

**Warnings:**

- **`/MIR`** deletes files in the OneDrive `TEMP` tree that are not in `C:\TEMP`. This is intentional for a true mirror; do not treat OneDrive `TEMP` as a scratch area for files that only live there.
- Full `C:\TEMP` can be **very large** (logs, backups, many files). Consider mirroring only `C:\TEMP\DV_Analysis` if you want a smaller, GIS-focused sync (would require a separate robocopy job or different source path).

**Log lock:** If robocopy logs to `...\TEMP\.mirror_logs\robocopy_last_run.log`, the first run may log **ERROR 32** when `/MIR` tries to remove that log as an “extra” file while it is open. Subsequent runs are usually clean; optional improvement is logging outside the destination tree.

---

## 5. Related docs

- [imported_sandbox_arcgis_note.md](imported_sandbox_arcgis_note.md) — sandbox import of `dv_doj` ArcGIS exports (gitignored tree).
- [CLAUDE.md §20–24](../CLAUDE.md) — ArcPy script table and known ArcGIS path issues.
