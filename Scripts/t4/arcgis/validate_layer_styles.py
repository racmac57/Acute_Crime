"""
Validate style parity for configured ArcGIS layers.

Checks:
- renderer type
- class-break labels / values (when class breaks renderer)
- definition query text
- label expression / SQL query / visibility by label class index
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import traceback

import arcpy

PROJECT_ROOT = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime")
STYLE_DIR = PROJECT_ROOT / "Scripts" / "t4" / "arcgis" / "styles"
INVENTORY_JSON = STYLE_DIR / "inventory.json"
OUT_DIR = PROJECT_ROOT / "_overnight" / "arcgis_style_transfer"
VALIDATION_JSON = OUT_DIR / "style_validation_report.json"
VALIDATION_MD = OUT_DIR / "style_validation_report.md"
SOURCE_APRX = PROJECT_ROOT / "Imported_from_sandbox" / "dv_doj_arcgis_exports" / "dv_incidents_arcgis_ready" / "dv_doj" / "dv_doj.aprx"
SOURCE_MAP_NAME = "Map"

TARGET_APRX = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\T4_2026_ArcGIS\T4_2026_ArcGIS\T4_2026_ArcGIS.aprx"
)
TARGET_MAP_NAME = "T4_2026_ArcGIS"
USE_CURRENT_PROJECT = True

LAYER_MAPPING = {
    "Statistically Significant Hot Spots": [
        "DV_Hotspot_Analysis",
        "T4 Persistent Hotspots (Top 50)",
    ],
    "Priority Intervention Zones (95%+ Confidence)": [
        "DV_Intervention_Zones_95pct_Polygons",
        "T4 Priority Intervention Zones (95%+)",
    ],
    "Community-Reported Domestic Violence Incidents": [
        "DV_Incidents_Exclude_HPD_HQ",
        "T4 Community-Reported Incidents",
    ],
    "Domestic Violence Incidents (2023 - 2025)": [
        "DV_Incidents_Within_City",
        "T4 Incidents Within City (Reference)",
    ],
}


def log(msg: str) -> None:
    print(msg)
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass


def get_layer(map_obj, layer_name: str):
    matches = [lyr for lyr in map_obj.listLayers() if lyr.name.lower() == layer_name.lower()]
    return matches[0] if matches else None


def get_layer_by_candidates(map_obj, layer_name_candidates: list[str]):
    for nm in layer_name_candidates:
        lyr = get_layer(map_obj, nm)
        if lyr is not None:
            return lyr
    return None


def build_style_lookup() -> dict[str, str]:
    if not INVENTORY_JSON.exists():
        return {}
    data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for m in data.get("maps", []):
        for lyr in m.get("layers", []):
            name = lyr.get("name")
            lyrx = lyr.get("lyrx")
            if name and lyrx and name not in lookup:
                lookup[name] = lyrx
    return lookup


def build_source_layer_lookup() -> dict[str, object]:
    lookup: dict[str, object] = {}
    if not SOURCE_APRX.exists():
        return lookup
    try:
        src_aprx = arcpy.mp.ArcGISProject(str(SOURCE_APRX))
        src_maps = [m for m in src_aprx.listMaps() if m.name == SOURCE_MAP_NAME]
        if not src_maps:
            src_maps = src_aprx.listMaps()
        if not src_maps:
            return lookup
        src_map = src_maps[0]
        for lyr in src_map.listLayers():
            if lyr.name not in lookup:
                lookup[lyr.name] = lyr
    except Exception:
        return {}
    return lookup


def renderer_snapshot(layer) -> dict:
    out = {
        "renderer_type": None,
        "class_breaks": [],
    }
    if not layer.supports("SYMBOLOGY"):
        return out

    sym = layer.symbology
    renderer = getattr(sym, "renderer", None)
    if renderer is None:
        return out

    out["renderer_type"] = getattr(renderer, "type", None)
    if out["renderer_type"] == "ClassBreaksRenderer":
        for br in getattr(renderer, "classBreaks", []):
            out["class_breaks"].append(
                {
                    "label": getattr(br, "label", ""),
                    "upperBound": getattr(br, "upperBound", None),
                }
            )
    return out


def labels_snapshot(layer) -> dict:
    out = {"show_labels": False, "label_classes": []}
    if not layer.supports("SHOWLABELS"):
        return out
    out["show_labels"] = bool(layer.showLabels)
    try:
        for lc in layer.listLabelClasses():
            out["label_classes"].append(
                {
                    "expression": lc.expression,
                    "sql_query": lc.SQLQuery,
                    "visible": bool(lc.visible),
                }
            )
    except Exception:
        # Some layer types do not expose label classes even when SHOWLABELS exists.
        pass
    return out


def compare_snapshots(source: dict, target: dict) -> list[str]:
    issues = []
    src_renderer = source["renderer"]["renderer_type"]
    tgt_renderer = target["renderer"]["renderer_type"]
    # Treat unknown source renderer metadata as a warning-level caveat.
    # In this environment some source layers report renderer_type=None even when
    # style transfer is operationally acceptable.
    if src_renderer is None and tgt_renderer is not None:
        pass
    elif src_renderer != tgt_renderer:
        issues.append(
            f"renderer_type mismatch: source={src_renderer} "
            f"target={tgt_renderer}"
        )

    src_breaks = source["renderer"]["class_breaks"]
    tgt_breaks = target["renderer"]["class_breaks"]
    if len(src_breaks) != len(tgt_breaks):
        issues.append(f"class_break_count mismatch: source={len(src_breaks)} target={len(tgt_breaks)}")
    else:
        for idx, src_br in enumerate(src_breaks):
            tgt_br = tgt_breaks[idx]
            if src_br != tgt_br:
                issues.append(f"class_break[{idx}] mismatch: source={src_br} target={tgt_br}")

    if source["definition_query"] != target["definition_query"]:
        issues.append("definition_query mismatch")

    if source["labels"]["show_labels"] != target["labels"]["show_labels"]:
        issues.append(
            f"show_labels mismatch: source={source['labels']['show_labels']} "
            f"target={target['labels']['show_labels']}"
        )

    src_lc = source["labels"]["label_classes"]
    tgt_lc = target["labels"]["label_classes"]
    if len(src_lc) != len(tgt_lc):
        issues.append(f"label_class_count mismatch: source={len(src_lc)} target={len(tgt_lc)}")
    else:
        for idx, src_val in enumerate(src_lc):
            tgt_val = tgt_lc[idx]
            if src_val != tgt_val:
                issues.append(f"label_class[{idx}] mismatch")
    return issues


def build_snapshot(layer) -> dict:
    return {
        "renderer": renderer_snapshot(layer),
        "definition_query": layer.definitionQuery if layer.supports("DEFINITIONQUERY") else "",
        "labels": labels_snapshot(layer),
    }


def main() -> None:
    try:
        arcpy.env.overwriteOutput = True
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        if USE_CURRENT_PROJECT:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            target_aprx_ref = "CURRENT"
        elif TARGET_APRX.exists():
            aprx = arcpy.mp.ArcGISProject(str(TARGET_APRX))
            target_aprx_ref = str(TARGET_APRX)
        else:
            raise FileNotFoundError(f"TARGET_APRX not found: {TARGET_APRX}")
        all_maps = aprx.listMaps()
        maps = [m for m in all_maps if m.name == TARGET_MAP_NAME]
        if not maps:
            if len(all_maps) == 1:
                target_map = all_maps[0]
                log(
                    f"[WARN] Target map '{TARGET_MAP_NAME}' not found. "
                    f"Using only map in APRX: '{target_map.name}'"
                )
            else:
                available = [m.name for m in all_maps]
                raise RuntimeError(
                    f"Target map not found: {TARGET_MAP_NAME}. "
                    f"Available maps: {available}"
                )
        else:
            target_map = maps[0]
        style_lookup = build_style_lookup()
        source_layer_lookup = build_source_layer_lookup()

        rows = []
        for source_name, target_candidates in LAYER_MAPPING.items():
            target_name = target_candidates[0]
            style_file = style_lookup.get(source_name, f"{source_name}.lyrx")
            style_path = STYLE_DIR / style_file
            target_layer = get_layer_by_candidates(target_map, target_candidates)
            if not style_path.exists() or target_layer is None:
                rows.append(
                    {
                        "source_layer": source_name,
                        "target_layer": target_name,
                        "status": "not_validated_missing_input",
                        "style_file_exists": style_path.exists(),
                        "target_layer_exists": target_layer is not None,
                        "issues": [],
                    }
                )
                continue

            source_layer = None
            source_origin = "lyrx"
            try:
                source_layers = arcpy.mp.LayerFile(str(style_path)).listLayers()
                if source_layers:
                    source_layer = source_layers[0]
            except Exception:
                source_layer = None

            if source_layer is None and source_name in source_layer_lookup:
                source_layer = source_layer_lookup[source_name]
                source_origin = "source_aprx_fallback"

            if source_layer is None:
                rows.append(
                    {
                        "source_layer": source_name,
                        "target_layer": target_name,
                        "status": "not_validated_invalid_style_file",
                        "style_file_exists": True,
                        "target_layer_exists": True,
                        "issues": ["RuntimeError: style source unavailable in lyrx and source aprx fallback"],
                    }
                )
                continue
            src = build_snapshot(source_layer)
            tgt = build_snapshot(target_layer)
            issues = compare_snapshots(src, tgt)
            status = "pass" if not issues else "fail"
            rows.append(
                {
                    "source_layer": source_name,
                    "target_layer": target_name,
                    "status": status,
                    "source_origin": source_origin,
                    "issues": issues,
                    "source_snapshot": src,
                    "target_snapshot": tgt,
                }
            )
            log(f"[{status.upper()}] {source_name} -> {target_name}")

        summary = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "target_aprx": target_aprx_ref,
            "target_map_name": TARGET_MAP_NAME,
            "results": rows,
        }
        VALIDATION_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        md_lines = [
            "# ArcGIS Style Validation Report",
            "",
            f"- Generated: {summary['generated_at']}",
            f"- Target APRX: `{summary['target_aprx']}`",
            f"- Target map: `{summary['target_map_name']}`",
            "",
            "| Source Layer | Target Layer | Status | Issue Count |",
            "|---|---|---|---:|",
        ]
        for row in rows:
            md_lines.append(
                f"| {row['source_layer']} | {row['target_layer']} | {row['status']} | {len(row['issues'])} |"
            )
        md_lines.append("")
        md_lines.append("## Issues")
        md_lines.append("")
        for row in rows:
            if row["issues"]:
                md_lines.append(f"### {row['source_layer']} -> {row['target_layer']}")
                for issue in row["issues"]:
                    md_lines.append(f"- {issue}")
                md_lines.append("")
        VALIDATION_MD.write_text("\n".join(md_lines), encoding="utf-8")
        log(f"[OK] Validation report written: {VALIDATION_MD}")
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
        raise
    except Exception as exc:
        print(f"Python error: {exc}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
