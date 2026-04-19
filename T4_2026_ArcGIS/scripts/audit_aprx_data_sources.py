# -*- coding: utf-8 -*-
"""
audit_aprx_data_sources.py

Run in ArcGIS Pro (arcgispro-py3). Exports layer/table data sources for an .aprx
so you can compare machines or drive a repair workflow.

If you paste this into the Python window (not Run Script), __file__ is undefined;
T4_ROOT_FALLBACK is used — edit it if your paths differ.

Default paths target this repo's T4 project; override via CONFIG or argv:
  propy.bat audit_aprx_data_sources.py "D:\\Other\\project.aprx"
"""

from __future__ import annotations

import arcpy
import json
import sys
from pathlib import Path

# --- CONFIG (edit or pass .aprx as first argument) ---------------------------------
# Pasting this script into the Pro Python window leaves __file__ undefined; we fall back
# to T4_ROOT_FALLBACK. Change that path if your project lives elsewhere.
T4_ROOT_FALLBACK = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime"
    r"\T4_2026_ArcGIS"
)
try:
    _T4_ROOT = Path(__file__).resolve().parents[1]
except NameError:
    _T4_ROOT = T4_ROOT_FALLBACK

APRX_PATH = str(_T4_ROOT / "T4_2026_ArcGIS" / "T4_2026_ArcGIS.aprx")
# Written next to the .aprx unless you set an explicit path
OUTPUT_JSON: str | None = None  # e.g. r"D:\GIS\datasource_manifest.json"
# ------------------------------------------------------------------------------------


def _json_safe(obj):
    """Best-effort structure for json.dump; falls back to str for odd values."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return str(obj)


def _connection_properties_safe(lyr_or_tbl) -> dict | None:
    try:
        return _json_safe(lyr_or_tbl.connectionProperties)
    except Exception:
        return None


def _layer_entry(map_name: str, lyr) -> dict:
    entry: dict = {
        "map_name": map_name,
        "kind": "layer",
        "name": lyr.name,
        "long_name": getattr(lyr, "longName", None) or lyr.name,
        "is_group_layer": bool(getattr(lyr, "isGroupLayer", False)),
        "is_broken": bool(getattr(lyr, "isBroken", False)),
        "data_source": None,
        "catalog_path": None,
        "connection_properties": None,
    }
    if entry["is_group_layer"]:
        return entry
    if lyr.supports("DATASOURCE"):
        entry["data_source"] = getattr(lyr, "dataSource", None)
        entry["catalog_path"] = getattr(lyr, "catalogPath", None) or None
    entry["connection_properties"] = _connection_properties_safe(lyr)
    return entry


def _table_entry(map_name: str, tbl) -> dict:
    entry: dict = {
        "map_name": map_name,
        "kind": "table",
        "name": tbl.name,
        "long_name": getattr(tbl, "longName", None) or tbl.name,
        "is_group_layer": False,
        "is_broken": bool(getattr(tbl, "isBroken", False)),
        "data_source": None,
        "catalog_path": None,
        "connection_properties": None,
    }
    if tbl.supports("DATASOURCE"):
        entry["data_source"] = getattr(tbl, "dataSource", None)
        entry["catalog_path"] = getattr(tbl, "catalogPath", None) or None
    entry["connection_properties"] = _connection_properties_safe(tbl)
    return entry


def audit(aprx_path: str, output_json: str | None) -> Path:
    aprx_path = str(Path(aprx_path))
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    manifest: list[dict] = []

    for m in aprx.listMaps():
        for lyr in m.listLayers():
            manifest.append(_layer_entry(m.name, lyr))
        for tbl in m.listTables():
            manifest.append(_table_entry(m.name, tbl))

    out = Path(output_json) if output_json else Path(aprx_path).with_name(
        "datasource_manifest.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    for e in manifest:
        if e.get("is_group_layer"):
            continue
        tag = "BROKEN" if e.get("is_broken") else "OK"
        print(f"[{tag}] {e['map_name']} :: {e['long_name']}")
        if e.get("data_source"):
            print(f"        {e['data_source']}")

    print(f"\nManifest written -> {out}")
    return out


def main() -> None:
    aprx = sys.argv[1] if len(sys.argv) > 1 else APRX_PATH
    out = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_JSON
    audit(aprx, out)


if __name__ == "__main__":
    main()
