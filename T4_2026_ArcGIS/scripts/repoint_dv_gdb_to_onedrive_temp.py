# -*- coding: utf-8 -*-
"""
repoint_dv_gdb_to_onedrive_temp.py

Run inside ArcGIS Pro (arcgispro-py3). Repoints map layers/tables that use
  C:\\TEMP\\DV_Analysis\\dv_doj.gdb
to the mirrored file geodatabase under OneDrive:
  %USERPROFILE%\\OneDrive - City of Hackensack\\TEMP\\DV_Analysis\\dv_doj.gdb

Primary method: layer/table ``connectionProperties['connection_info']['database']``
replace (Esri dictionary pattern). Project-level ``updateConnectionProperties``
can report success but no-op when internal path strings do not match exactly.

See: https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/updatingandfixingdatasources.htm
"""

from __future__ import annotations

import arcpy
import copy
import os
import sys
from pathlib import Path

# --- CONFIG -------------------------------------------------------------------------
T4_ROOT_FALLBACK = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime"
    r"\T4_2026_ArcGIS"
)
try:
    _T4_ROOT = Path(__file__).resolve().parents[1]
except NameError:
    _T4_ROOT = T4_ROOT_FALLBACK

APRX_PATH = str(_T4_ROOT / "T4_2026_ArcGIS" / "T4_2026_ArcGIS.aprx")

OLD_DV_GDB = r"C:\TEMP\DV_Analysis\dv_doj.gdb"

NEW_DV_GDB = os.path.join(
    os.environ.get("USERPROFILE", ""),
    r"OneDrive - City of Hackensack\TEMP\DV_Analysis\dv_doj.gdb",
)

VALIDATE_NEW_PATH = True

SAVE_IN_PLACE = False

# Also run project-level find/replace (may help joins; layer loop is authoritative).
RUN_PROJECT_LEVEL_TOO = True
# ------------------------------------------------------------------------------------


def _norm_db(p: str) -> str:
    return os.path.normcase(os.path.normpath(p))


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


def _repoint_object(obj, old_gdb: str, new_gdb: str) -> bool:
    """Return True if this layer/table was updated."""
    try:
        cp = obj.connectionProperties
    except Exception:
        return False
    if not isinstance(cp, dict):
        return False
    ci = cp.get("connection_info")
    if not isinstance(ci, dict):
        return False
    db = ci.get("database")
    if not db or not isinstance(db, str):
        return False
    if _norm_db(db) != _norm_db(old_gdb):
        return False
    old_cp = copy.deepcopy(cp)
    new_cp = copy.deepcopy(cp)
    new_cp.setdefault("connection_info", {})["database"] = new_gdb
    try:
        obj.updateConnectionProperties(old_cp, new_cp)
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
        raise
    return True


def _repoint_all_maps(aprx: arcpy.mp.ArcGISProject, old_gdb: str, new_gdb: str) -> int:
    n = 0
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isGroupLayer:
                continue
            if _repoint_object(lyr, old_gdb, new_gdb):
                print(f"  [updated dict] {m.name} :: {lyr.longName}")
                n += 1
        for tbl in m.listTables():
            if _repoint_object(tbl, old_gdb, new_gdb):
                print(f"  [updated dict] {m.name} :: TABLE {tbl.name}")
                n += 1
    return n


def _datasource_uses_gdb(ds: str, old_gdb: str) -> bool:
    if not ds:
        return False
    a = os.path.normcase(os.path.normpath(old_gdb))
    # dataSource is often: ...\dv_doj.gdb\FeatureClassName
    b = ds.replace("/", "\\")
    return a in os.path.normcase(b) or old_gdb.lower() in b.lower()


def _repoint_string_fallback(aprx: arcpy.mp.ArcGISProject, old_gdb: str, new_gdb: str) -> int:
    """Per-layer workspace strings (Esri help example for broken layers)."""
    n = 0
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isGroupLayer:
                continue
            if not lyr.supports("DATASOURCE"):
                continue
            try:
                ds = lyr.dataSource or ""
            except Exception:
                continue
            if not _datasource_uses_gdb(ds, old_gdb):
                continue
            try:
                lyr.updateConnectionProperties(old_gdb, new_gdb)
                print(f"  [updated str] {m.name} :: {lyr.longName}")
                n += 1
            except Exception as ex:
                print(f"  [skip str] {lyr.name}: {ex}")
        for tbl in m.listTables():
            if not tbl.supports("DATASOURCE"):
                continue
            try:
                ds = tbl.dataSource or ""
            except Exception:
                continue
            if not _datasource_uses_gdb(ds, old_gdb):
                continue
            try:
                tbl.updateConnectionProperties(old_gdb, new_gdb)
                print(f"  [updated str] {m.name} :: TABLE {tbl.name}")
                n += 1
            except Exception as ex:
                print(f"  [skip str] TABLE {tbl.name}: {ex}")
    return n


def _project_level(aprx: arcpy.mp.ArcGISProject, old: str, new: str, *, validate: bool) -> None:
    print(f"Project updateConnectionProperties:\n  FROM: {old}\n    TO: {new}")
    try:
        try:
            aprx.updateConnectionProperties(
                old,
                new,
                auto_update_joins_and_relates=True,
                validate=validate,
                ignore_case=True,
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


def _sample_database_paths(aprx: arcpy.mp.ArcGISProject, label: str, max_print: int = 4) -> None:
    print(f"\n--- Sample connection_info.database ({label}) ---")
    shown = 0
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isGroupLayer:
                continue
            try:
                cp = lyr.connectionProperties
                ci = (cp or {}).get("connection_info") or {}
                db = ci.get("database")
                if db and "dv_doj" in str(db).lower():
                    print(f"  {lyr.name}: {db}")
                    shown += 1
                    if shown >= max_print:
                        return
            except Exception:
                pass


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

    print("Before repair — broken count:", len(_report_broken(aprx)))
    _sample_database_paths(aprx, "before")

    if RUN_PROJECT_LEVEL_TOO:
        _project_level(aprx, OLD_DV_GDB, new_gdb, validate=VALIDATE_NEW_PATH)

    print("\nLayer/table connectionProperties replace (dictionary):")
    count = _repoint_all_maps(aprx, OLD_DV_GDB, new_gdb)

    print("\nLayer/table string fallback (dataSource contains GDB path):")
    count2 = _repoint_string_fallback(aprx, OLD_DV_GDB, new_gdb)
    total = count + count2
    if total == 0:
        print(
            "  No layers updated.\n"
            "  Run audit_aprx_data_sources.py and inspect connection_properties in datasource_manifest.json\n"
            "  for the exact database string Pro stored."
        )
    else:
        print(f"\nUpdated {total} layer/table operation(s) (dict={count}, str={count2}).")

    _sample_database_paths(aprx, "after")

    after_broken = _report_broken(aprx)
    if after_broken:
        print(f"\nStill broken ({len(after_broken)}):")
        for line in after_broken:
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
        print("Close other ArcGIS Pro sessions, open THIS file, and check Layer Properties -> Source.")


if __name__ == "__main__":
    main()
