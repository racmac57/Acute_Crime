"""
Phase 1 ArcGIS style-transfer extraction (read-only to source APRX/GDB).

What this script does:
1) Inventories maps/layers/layouts in SOURCE_APRX
2) Exports .lyrx files for all transferable layers (non group/basemap/web)
3) Writes inventory + export summary for operator review

Design constraints:
- Never save the source APRX
- No geoprocessing writes to source GDB
- Good-enough operational artifact extraction for downstream reuse
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import traceback

import arcpy

# Read-only source project (do not edit this APRX/GDB in this workflow).
SOURCE_APRX = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\Imported_from_sandbox\dv_doj_arcgis_exports\dv_incidents_arcgis_ready\dv_doj\dv_doj.aprx"
)

PROJECT_ROOT = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime")
# Keep style artifacts in repo path for repeatable reuse.
STYLE_DIR = PROJECT_ROOT / "Scripts" / "t4" / "arcgis" / "styles"
INVENTORY_JSON = STYLE_DIR / "inventory.json"
EXPORT_SUMMARY = STYLE_DIR / "export_summary.json"

# Phase-1 operational shortlist candidates (for operator pick after extraction).
SHORTLIST_NAME_HINTS = [
    "hotspot",
    "post",
    "zone",
    "grid",
    "boundary",
]


def log(msg: str) -> None:
    print(msg)
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass


def safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)[:100]


def inventory_and_export(aprx: arcpy.mp.ArcGISProject) -> tuple[dict, dict]:
    inventory = {
        "source_aprx": str(SOURCE_APRX),
        "pro_version": arcpy.GetInstallInfo().get("Version"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "maps": [],
        "layouts": [],
    }
    export_count = 0
    skipped_count = 0
    error_count = 0
    shortlist_candidates: list[dict] = []

    for m in aprx.listMaps():
        map_record = {
            "name": m.name,
            "spatial_ref": getattr(m.spatialReference, "name", None),
            "layers": [],
        }
        for lyr in m.listLayers():
            is_group = bool(getattr(lyr, "isGroupLayer", False))
            is_basemap = bool(getattr(lyr, "isBasemapLayer", False))
            is_web = bool(getattr(lyr, "isWebLayer", False))
            if is_group or is_basemap or is_web:
                map_record["layers"].append(
                    {
                        "name": lyr.name,
                        "skipped": "group/basemap/web",
                        "is_group_layer": is_group,
                        "is_basemap_layer": is_basemap,
                        "is_web_layer": is_web,
                    }
                )
                skipped_count += 1
                continue

            supports_labels = lyr.supports("SHOWLABELS")
            supports_def = lyr.supports("DEFINITIONQUERY")
            def_query = lyr.definitionQuery if supports_def else ""
            layer_record = {
                "name": lyr.name,
                "is_feature_layer": bool(getattr(lyr, "isFeatureLayer", False)),
                "is_raster_layer": bool(getattr(lyr, "isRasterLayer", False)),
                "supports_symbology": lyr.supports("SYMBOLOGY"),
                "show_labels": bool(getattr(lyr, "showLabels", False)) if supports_labels else None,
                "definition_query": def_query or "",
                "data_source": getattr(lyr, "dataSource", None),
                "lyrx": None,
                "error": None,
            }
            out_lyrx = STYLE_DIR / f"{safe_name(m.name)}__{safe_name(lyr.name)}.lyrx"
            try:
                arcpy.management.SaveToLayerFile(lyr, str(out_lyrx), "ABSOLUTE")
                layer_record["lyrx"] = out_lyrx.name
                export_count += 1
                lname = lyr.name.lower()
                if any(h in lname for h in SHORTLIST_NAME_HINTS):
                    shortlist_candidates.append(
                        {"map_name": m.name, "layer_name": lyr.name, "lyrx": out_lyrx.name}
                    )
            except Exception as exc:
                layer_record["error"] = f"{type(exc).__name__}: {exc}"
                error_count += 1
                log(f"[WARN] Export failed for {m.name}::{lyr.name} -> {exc}")
            map_record["layers"].append(layer_record)
        inventory["maps"].append(map_record)

    for lay in aprx.listLayouts():
        inventory["layouts"].append(
            {
                "name": lay.name,
                "page_w_in": lay.pageWidth,
                "page_h_in": lay.pageHeight,
                "units": str(lay.pageUnits),
            }
        )

    summary = {
        "generated_at": inventory["generated_at"],
        "source_aprx": str(SOURCE_APRX),
        "pro_version": inventory["pro_version"],
        "exported_layer_count": export_count,
        "skipped_layer_count": skipped_count,
        "error_layer_count": error_count,
        "map_count": len(inventory["maps"]),
        "layout_count": len(inventory["layouts"]),
        "shortlist_candidates_by_name_hint": shortlist_candidates[:12],
    }
    return inventory, summary


def main() -> None:
    try:
        arcpy.env.overwriteOutput = True
        STYLE_DIR.mkdir(parents=True, exist_ok=True)

        if not SOURCE_APRX.exists():
            raise FileNotFoundError(f"Source APRX not found: {SOURCE_APRX}")

        log(f"[INFO] Loading source APRX (read-only): {SOURCE_APRX}")
        aprx = arcpy.mp.ArcGISProject(str(SOURCE_APRX))

        inventory, summary = inventory_and_export(aprx)
        INVENTORY_JSON.write_text(json.dumps(inventory, indent=2, default=str), encoding="utf-8")
        log(f"[OK] Inventory written: {INVENTORY_JSON}")
        EXPORT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        log(f"[OK] Export summary written: {EXPORT_SUMMARY}")
        log(f"[OK] Exported layers: {summary['exported_layer_count']}")

        # Explicitly release handle without saving source APRX.
        del aprx
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
        raise
    except Exception as exc:
        print(f"Python error: {exc}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
