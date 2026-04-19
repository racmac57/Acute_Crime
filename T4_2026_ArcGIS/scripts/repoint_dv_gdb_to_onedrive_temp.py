# -*- coding: utf-8 -*-
"""
repoint_dv_gdb_to_onedrive_temp.py

Run inside ArcGIS Pro (arcgispro-py3). Repoints map layers/tables that use
  C:\\TEMP\\DV_Analysis\\dv_doj.gdb
to the mirrored file geodatabase under OneDrive:
  %USERPROFILE%\\OneDrive - City of Hackensack\\TEMP\\DV_Analysis\\dv_doj.gdb

Uses ArcGISProject.updateConnectionProperties(workspace_old, workspace_new).
See: https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/updatingandfixingdatasources.htm

After a dry run, set SAVE_IN_PLACE = True to overwrite the .aprx, or keep False
to write a sibling *_onedrive_temp.aprx.
"""

from __future__ import annotations

import arcpy
import os
import sys
from pathlib import Path

# --- CONFIG -------------------------------------------------------------------------
# Pasting into the Pro Python window leaves __file__ undefined.
T4_ROOT_FALLBACK = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime"
    r"\T4_2026_ArcGIS"
)
try:
    _T4_ROOT = Path(__file__).resolve().parents[1]
except NameError:
    _T4_ROOT = T4_ROOT_FALLBACK

APRX_PATH = str(_T4_ROOT / "T4_2026_ArcGIS" / "T4_2026_ArcGIS.aprx")

# Source workspace recorded in the project (desktop / analysis machine).
OLD_DV_GDB = r"C:\TEMP\DV_Analysis\dv_doj.gdb"

# Mirrored GDB under OneDrive TEMP (same relative path as C:\TEMP\...).
NEW_DV_GDB = os.path.join(
    os.environ.get("USERPROFILE", ""),
    r"OneDrive - City of Hackensack\TEMP\DV_Analysis\dv_doj.gdb",
)

# If True, Pro only updates when NEW_DV_GDB exists on disk.
VALIDATE_NEW_PATH = True

# False: write T4_2026_ArcGIS_onedrive_temp.aprx next to the project.
# True:  aprx.save() — overwrites the opened .aprx path.
SAVE_IN_PLACE = False
# ------------------------------------------------------------------------------------


def _report_broken(aprx: arcpy.mp.ArcGISProject) -> list[str]:
    bad: list[str] = []
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isGroupLayer:
                continue
            if lyr.isBroken:
                ds = lyr.dataSource if lyr.supports("DATASOURCE") else ""
                bad.append(f"{m.name} :: {lyr.longName} | {ds}")
        for tbl in m.listTables():
            if tbl.isBroken:
                ds = tbl.dataSource if tbl.supports("DATASOURCE") else ""
                bad.append(f"{m.name} :: TABLE {tbl.name} | {ds}")
    return bad


def _ucp(aprx: arcpy.mp.ArcGISProject, old: str, new: str, *, validate: bool) -> None:
    print(f"updateConnectionProperties:\n  FROM: {old}\n    TO: {new}")
    try:
        try:
            aprx.updateConnectionProperties(
                old,
                new,
                auto_update_joins_and_relates=True,
                validate=validate,
                ignore_case=False,
            )
        except TypeError:
            aprx.updateConnectionProperties(
                old,
                new,
                auto_update_joins_and_relates=True,
                validate=validate,
            )
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
        raise


def main() -> None:
    aprx_path = sys.argv[1] if len(sys.argv) > 1 else APRX_PATH
    save_in_place = SAVE_IN_PLACE
    if len(sys.argv) > 2 and sys.argv[2].lower() in ("--save", "--in-place", "-i"):
        save_in_place = True

    new_gdb = NEW_DV_GDB
    if not new_gdb or not os.path.dirname(new_gdb):
        raise SystemExit("USERPROFILE missing; cannot build OneDrive TEMP path to dv_doj.gdb.")

    if VALIDATE_NEW_PATH and not Path(new_gdb).exists():
        raise SystemExit(
            f"New GDB not found (required when VALIDATE_NEW_PATH is True):\n  {new_gdb}\n"
            "Mirror C:\\TEMP to OneDrive TEMP first, or set VALIDATE_NEW_PATH = False."
        )

    aprx = arcpy.mp.ArcGISProject(aprx_path)
    before = _report_broken(aprx)
    if before:
        print(f"Broken before repair ({len(before)}):")
        for line in before:
            print(f"  {line}")
    else:
        print("No broken layers/tables reported before repair (paths may already match).")

    _ucp(aprx, OLD_DV_GDB, new_gdb, validate=VALIDATE_NEW_PATH)

    after = _report_broken(aprx)
    if after:
        print(f"\nStill broken ({len(after)}):")
        for line in after:
            print(f"  {line}")
    else:
        print("\nAll layers/tables report not broken.")

    out_base = Path(aprx_path)
    if save_in_place:
        aprx.save()
        print(f"\nSaved in place -> {aprx_path}")
    else:
        out_path = out_base.with_name(out_base.stem + "_onedrive_temp.aprx")
        aprx.saveACopy(str(out_path))
        print(f"\nSaved copy -> {out_path}")
        print("Open the copy to confirm, then set SAVE_IN_PLACE = True or pass --save to overwrite the original.")


if __name__ == "__main__":
    main()
