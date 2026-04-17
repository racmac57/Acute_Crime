"""
reconnect_layers.py
===================
Reconnects broken data-source paths in T4_2026_ArcGIS.aprx.

Background
----------
The layers were originally created with data at C:\\TEMP\\DV_Analysis\\dv_doj.gdb\\
That temp path does not exist on this machine.  This script:

  1. DIAGNOSE  — opens the APRX and prints every layer's current data source
                 and whether it is broken, so you can confirm the new GDB path.
  2. RECONNECT — updates each broken layer's connection to the new GDB path
                 and saves the project.

Usage
-----
Run from the ArcGIS Pro Python window  (easiest):

    exec(open(r"C:\\Users\\carucci_r\\OneDrive - City of Hackensack\\10_Projects"
              r"\\Acute_Crime\\Scripts\\t4\\arcgis\\reconnect_layers.py").read())

Or run from the ArcGIS Pro conda prompt:
    cd "C:\\Users\\carucci_r\\OneDrive - City of Hackensack\\10_Projects\\Acute_Crime"
    python Scripts\\t4\\arcgis\\reconnect_layers.py

Configuration
-------------
Set NEW_GDB_PATH below to wherever dv_doj.gdb now lives on this machine.
If you are unsure, run with MODE = "diagnose" first to see the broken paths.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

import arcpy

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — edit these two lines before running
# ─────────────────────────────────────────────────────────────────────────────

# "diagnose"  → print layer sources only, no changes made
# "reconnect" → update broken sources and save
MODE = "reconnect"

APRX_PATH = (
    r"C:\Users\carucci_r\OneDrive - City of Hackensack"
    r"\10_Projects\Acute_Crime\T4_2026_ArcGIS\T4_2026_ArcGIS\T4_2026_ArcGIS.aprx"
)

# Path to the GDB on THIS machine.
# The script will auto-scan common locations; set this explicitly if needed.
# e.g. r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\T4_2026_ArcGIS\T4_2026_ArcGIS\T4_2026_ArcGIS.gdb"
NEW_GDB_PATH = ""   # leave blank to trigger auto-detect

# ─────────────────────────────────────────────────────────────────────────────

# The broken old root that was on the original machine
OLD_GDB_PATH = r"C:\TEMP\DV_Analysis\dv_doj.gdb"

# Feature class names that need to be reconnected (from inventory.json)
LAYER_TO_FC = {
    "Domestic Violence Incidents (2023 - 2025)":        "DV_Incidents_Within_City",
    "Statistically Significant Hot Spots":              "DV_Hotspot_Analysis",
    "Priority Intervention Zones (95%+ Confidence)":    "DV_Intervention_Zones_95pct_Polygons",
    "Community-Reported Domestic Violence Incidents":   "DV_Incidents_Exclude_HPD_HQ",
    # Operational renamed versions (same FCs, different layer names)
    "T4 Incidents Within City (Reference)":             "DV_Incidents_Within_City",
    "T4 Persistent Hotspots (Top 50)":                  "DV_Hotspot_Analysis",
    "T4 Priority Intervention Zones (95%+)":            "DV_Intervention_Zones_95pct_Polygons",
    "T4 Community-Reported Incidents":                  "DV_Incidents_Exclude_HPD_HQ",
}


def log(msg: str) -> None:
    print(msg)
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass


def auto_detect_gdb() -> str:
    """
    Scan common locations for dv_doj.gdb and return the first match.
    Returns empty string if not found.
    """
    project_root = Path(
        r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime"
    )
    candidates = [
        # Default project geodatabase
        Path(APRX_PATH).parent / "T4_2026_ArcGIS.gdb",
        # Imported sandbox export location
        project_root / "Imported_from_sandbox" / "dv_doj_arcgis_exports"
                     / "dv_incidents_arcgis_ready" / "dv_doj" / "dv_doj.gdb",
        # Data subfolder
        project_root / "Data" / "gdb" / "dv_doj.gdb",
        project_root / "Data" / "dv_doj.gdb",
        # T4 ArcGIS project folder
        Path(APRX_PATH).parent.parent / "dv_doj.gdb",
    ]
    for c in candidates:
        if c.exists():
            log(f"[AUTO-DETECT] Found GDB at: {c}")
            return str(c)
    return ""


def diagnose(aprx) -> list[dict]:
    rows = []
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isGroupLayer or lyr.isBasemapLayer or lyr.isWebLayer:
                continue
            try:
                cp = lyr.connectionProperties
                datasource = lyr.dataSource if hasattr(lyr, "dataSource") else ""
            except Exception:
                cp = None
                datasource = ""
            broken = not lyr.supports("DATASOURCE") or (
                datasource and not os.path.exists(
                    datasource.split("\\DV_")[0] if "\\DV_" in datasource else datasource
                )
            )
            rows.append(
                {
                    "map": m.name,
                    "layer": lyr.name,
                    "datasource": datasource,
                    "broken": broken,
                    "cp": cp,
                }
            )
    return rows


def reconnect(aprx, new_gdb: str) -> None:
    gdb_path = Path(new_gdb)
    if not gdb_path.exists():
        raise FileNotFoundError(
            f"\nGDB not found: {new_gdb}\n"
            "Set NEW_GDB_PATH at the top of this script to the correct location."
        )

    fixed = 0
    skipped = 0
    failed = 0

    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isGroupLayer or lyr.isBasemapLayer or lyr.isWebLayer:
                continue

            layer_name = lyr.name
            fc_name = LAYER_TO_FC.get(layer_name)
            if fc_name is None:
                # Try to derive from current datasource path
                try:
                    ds = lyr.dataSource
                    if OLD_GDB_PATH.lower() in ds.lower():
                        fc_name = Path(ds).name  # last component is the FC name
                    else:
                        skipped += 1
                        continue
                except Exception:
                    skipped += 1
                    continue

            new_fc_path = str(gdb_path / fc_name)
            if not arcpy.Exists(new_fc_path):
                log(f"  [WARN] FC not found in new GDB: {fc_name}  (layer: {layer_name})")
                failed += 1
                continue

            try:
                cp = lyr.connectionProperties
                new_cp = cp.copy() if cp else {}

                # Build a clean workspace connection dict pointing to new GDB
                new_cp["connection_info"] = {"database": str(gdb_path)}
                new_cp["dataset"] = fc_name
                new_cp["workspace_factory"] = "File Geodatabase"

                lyr.updateConnectionProperties(cp, new_cp)
                log(f"  [OK]  {layer_name}  →  {fc_name}")
                fixed += 1
            except Exception as exc:
                log(f"  [FAIL] {layer_name}: {type(exc).__name__}: {exc}")
                failed += 1

    log(f"\nResult: {fixed} reconnected | {skipped} skipped (not in map) | {failed} failed")

    if fixed > 0:
        try:
            aprx.save()
            log("[OK] Project saved.")
        except Exception as exc:
            log(
                f"[WARN] Save failed ({type(exc).__name__}: {exc}).\n"
                "       The reconnections are live in the current session — "
                "use File > Save in ArcGIS Pro to persist them."
            )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    arcpy.env.overwriteOutput = True

    log(f"\n{'='*60}")
    log(f"T4 Layer Reconnect Utility  |  mode={MODE}")
    log(f"{'='*60}")

    # Open project — use CURRENT if running inside ArcGIS Pro Python window
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        log("[INFO] Using currently open ArcGIS Pro project.")
    except Exception:
        if not os.path.exists(APRX_PATH):
            log(f"[ERROR] APRX not found: {APRX_PATH}")
            sys.exit(1)
        aprx = arcpy.mp.ArcGISProject(APRX_PATH)
        log(f"[INFO] Opened: {APRX_PATH}")

    # ── DIAGNOSE ──────────────────────────────────────────────────────────────
    log("\n── Layer Data Source Inventory ──")
    rows = diagnose(aprx)
    broken_count = 0
    for r in rows:
        status = "BROKEN" if r["broken"] else "ok"
        if r["broken"]:
            broken_count += 1
        log(f"  [{status:6s}]  {r['map']} / {r['layer']}")
        if r["datasource"]:
            log(f"            {r['datasource']}")

    log(f"\n{broken_count} broken layer(s) found out of {len(rows)} total.\n")

    if MODE == "diagnose":
        log("MODE=diagnose — no changes made.")
        log("Set MODE='reconnect' and NEW_GDB_PATH to fix the broken sources.")
        return

    # ── RECONNECT ─────────────────────────────────────────────────────────────
    gdb = NEW_GDB_PATH.strip()
    if not gdb:
        gdb = auto_detect_gdb()
    if not gdb:
        log(
            "\n[ERROR] Could not auto-detect dv_doj.gdb.\n"
            "Set NEW_GDB_PATH at the top of this script to the full path of\n"
            "the GDB on this machine and run again."
        )
        sys.exit(1)

    log(f"── Reconnecting layers to: {gdb}")
    reconnect(aprx, gdb)


if __name__ == "__main__":
    main()
