# -*- coding: utf-8 -*-
"""
repair_aprx_data_sources.py

Run on the machine where paths are WRONG (e.g. laptop) inside ArcGIS Pro.

Uses arcpy.mp.ArcGISProject.updateConnectionProperties with workspace strings
or partial path fragments per Esri's "Updating and fixing data sources" help.

Default output is a sibling *_repaired.aprx so the original synced file stays intact.

Optional: set PATH_REPLACEMENTS for several ordered find/replace steps
(e.g. username folder, then drive letter).
"""

from __future__ import annotations

import arcpy
import sys
from pathlib import Path

# --- CONFIG -------------------------------------------------------------------------
# See audit_aprx_data_sources.py — pasting into the Pro Python window has no __file__.
T4_ROOT_FALLBACK = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime"
    r"\T4_2026_ArcGIS"
)
try:
    _T4_ROOT = Path(__file__).resolve().parents[1]
except NameError:
    _T4_ROOT = T4_ROOT_FALLBACK

APRX_PATH = str(_T4_ROOT / "T4_2026_ArcGIS" / "T4_2026_ArcGIS.aprx")

OUTPUT_APRX = str(_T4_ROOT / "T4_2026_ArcGIS" / "T4_2026_ArcGIS_repaired.aprx")

# Ordered (current_substring, new_substring) pairs passed to updateConnectionProperties.
# Use FULL paths to the .gdb workspace when repointing file geodatabases (safest).
#
# T4 audit showed layers using desktop-only temp data — example fix after you copy
# dv_doj.gdb to the laptop (e.g. under this repo):
#   OLD: C:\TEMP\DV_Analysis\dv_doj.gdb
#   NEW: <folder you choose>\dv_doj.gdb  (must exist before repair if VALIDATE_NEW_PATH is True)
PATH_REPLACEMENTS: list[tuple[str, str]] = [
    # Uncomment and set NEW to match where dv_doj.gdb lives on this machine:
    # (
    #     r"C:\TEMP\DV_Analysis\dv_doj.gdb",
    #     r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\T4_2026_ArcGIS\T4_2026_ArcGIS\dv_doj.gdb",
    # ),
]

# If True, Pro verifies the new path exists before repointing. Set False only when
# you intentionally point ahead of data copy (layers may show broken until data exists).
VALIDATE_NEW_PATH = True

# Pass True for path compares that should ignore case (e.g. mixed-drive casing).
IGNORE_CASE = False
# ------------------------------------------------------------------------------------


def _report_broken(aprx: arcpy.mp.ArcGISProject, label: str) -> list[str]:
    bad: list[str] = []
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isGroupLayer:
                continue
            if lyr.isBroken:
                ds = lyr.dataSource if lyr.supports("DATASOURCE") else ""
                bad.append(f"{label}: {m.name} :: {lyr.longName} | {ds}")
        for tbl in m.listTables():
            if tbl.isBroken:
                ds = tbl.dataSource if tbl.supports("DATASOURCE") else ""
                bad.append(f"{label}: {m.name} :: TABLE {tbl.name} | {ds}")
    return bad


def repair(
    aprx_path: str,
    output_aprx: str,
    replacements: list[tuple[str, str]],
    *,
    validate: bool = True,
    ignore_case: bool = False,
) -> None:
    if not replacements:
        raise SystemExit(
            "PATH_REPLACEMENTS is empty. Edit repair_aprx_data_sources.py and add "
            "(old_prefix_or_workspace, new_prefix_or_workspace) tuples."
        )

    aprx = arcpy.mp.ArcGISProject(aprx_path)
    before = _report_broken(aprx, "before")

    for old, new in replacements:
        if not old:
            raise SystemExit("Replacement pairs must not contain an empty 'old' string.")
        print(f"updateConnectionProperties:\n  FROM: {old}\n    TO: {new}")
        try:
            try:
                aprx.updateConnectionProperties(
                    old,
                    new,
                    auto_update_joins_and_relates=True,
                    validate=validate,
                    ignore_case=ignore_case,
                )
            except TypeError:
                # Older Pro builds may not expose ignore_case on this method.
                aprx.updateConnectionProperties(
                    old,
                    new,
                    auto_update_joins_and_relates=True,
                    validate=validate,
                )
        except arcpy.ExecuteError:
            print(arcpy.GetMessages(2))
            raise
        except Exception as exc:
            print(f"Python error: {exc}")
            raise

    after = _report_broken(aprx, "after")

    if after:
        print("\nStill broken:")
        for line in after:
            print(f"  {line}")
    else:
        print("\nAll listed layers/tables report not broken.")

    if before and not after:
        print(f"\nResolved {len(before)} broken item(s) reported before repair.")

    out_path = Path(output_aprx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    aprx.saveACopy(str(out_path))
    print(f"\nSaved copy -> {out_path}")


def main() -> None:
    aprx = sys.argv[1] if len(sys.argv) > 1 else APRX_PATH
    out = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_APRX
    repair(
        aprx,
        out,
        PATH_REPLACEMENTS,
        validate=VALIDATE_NEW_PATH,
        ignore_case=IGNORE_CASE,
    )


if __name__ == "__main__":
    main()
