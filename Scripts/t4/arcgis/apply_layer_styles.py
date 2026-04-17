"""
Apply ArcGIS layer styles from exported .lyrx references to target map layers.

Scope for Phase 1:
- Symbology renderer
- Label classes / expression / visibility
- Definition query

No schema edits. No source APRX edits. Saves only TARGET_APRX copy.
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
APPLY_SUMMARY = OUT_DIR / "style_apply_summary.json"
SOURCE_APRX = PROJECT_ROOT / "Imported_from_sandbox" / "dv_doj_arcgis_exports" / "dv_incidents_arcgis_ready" / "dv_doj" / "dv_doj.aprx"
SOURCE_MAP_NAME = "Map"

# Target operational project/map.
TARGET_APRX = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime\T4_2026_ArcGIS\T4_2026_ArcGIS\T4_2026_ArcGIS.aprx"
)
TARGET_MAP_NAME = "T4_2026_ArcGIS"
USE_CURRENT_PROJECT = True

# Source layer style name -> target layer candidate names mapping.
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

# Post-apply renaming for operational readability in the map contents pane.
TARGET_RENAME_MAP = {
    "DV_Hotspot_Analysis": "T4 Persistent Hotspots (Top 50)",
    "DV_Intervention_Zones_95pct_Polygons": "T4 Priority Intervention Zones (95%+)",
    "DV_Incidents_Exclude_HPD_HQ": "T4 Community-Reported Incidents",
    "DV_Incidents_Within_City": "T4 Incidents Within City (Reference)",
}

# Cartographic tuning knobs (0-100, higher = more transparent).
LAYER_TRANSPARENCY_RULES = [
    {
        "candidates": ["T4 Persistent Hotspots (Top 50)", "DV_Hotspot_Analysis"],
        "transparency": 68,
    },
    {
        "candidates": ["T4 Priority Intervention Zones (95%+)", "DV_Intervention_Zones_95pct_Polygons"],
        "transparency": 78,
    },
    {
        "candidates": ["T4 Community-Reported Incidents", "DV_Incidents_Exclude_HPD_HQ"],
        "transparency": 15,
    },
]


def log(msg: str) -> None:
    print(msg)
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass


def get_layer(map_obj, layer_name: str):
    matches = [lyr for lyr in map_obj.listLayers() if lyr.name.lower() == layer_name.lower()]
    if not matches:
        return None
    return matches[0]


def get_layers_by_name(map_obj, layer_name: str):
    return [lyr for lyr in map_obj.listLayers() if lyr.name.lower() == layer_name.lower()]


def get_layers_by_prefix(map_obj, name_prefix: str):
    prefix = name_prefix.lower()
    return [lyr for lyr in map_obj.listLayers() if lyr.name.lower().startswith(prefix)]


def get_layer_by_candidates(map_obj, layer_name_candidates: list[str]):
    for nm in layer_name_candidates:
        lyr = get_layer(map_obj, nm)
        if lyr is not None:
            return lyr
    return None


def set_layer_visibility(layer, visible: bool) -> bool:
    try:
        if hasattr(layer, "visible"):
            layer.visible = visible
            return True
    except Exception:
        return False
    return False


def apply_layer_transparency_rules(map_obj) -> list[dict]:
    rows: list[dict] = []
    for rule in LAYER_TRANSPARENCY_RULES:
        value = int(rule.get("transparency", 0))
        applied = False
        for name in rule.get("candidates", []):
            lyr = get_layer(map_obj, name)
            if lyr is None:
                continue
            applied = True
            status = "applied"
            try:
                if hasattr(lyr, "transparency"):
                    lyr.transparency = value
                else:
                    status = "skipped_no_transparency_prop"
            except Exception as exc:
                status = f"failed:{type(exc).__name__}"
            rows.append(
                {
                    "layer": lyr.name,
                    "action": "set_transparency",
                    "value": value,
                    "status": status,
                }
            )
            break
        if not applied:
            rows.append(
                {
                    "layer": "|".join(rule.get("candidates", [])),
                    "action": "set_transparency",
                    "value": value,
                    "status": "missing_layer",
                }
            )
    return rows


def harden_hotspot_visuals(map_obj) -> dict:
    """
    Reduce hotspot fill clutter and improve 95% red visibility.
    """
    result = {
        "status": "not_run",
        "layer": "",
        "updates": [],
        "error": "",
    }
    hotspot = get_layer_by_candidates(
        map_obj,
        ["T4 Persistent Hotspots (Top 50)", "DV_Hotspot_Analysis"],
    )
    if hotspot is None:
        result["status"] = "missing_layer"
        return result

    result["layer"] = hotspot.name
    try:
        if not hotspot.supports("SYMBOLOGY"):
            result["status"] = "skipped_no_symbology"
            return result
        sym = hotspot.symbology
        renderer = getattr(sym, "renderer", None)
        if renderer is None:
            result["status"] = "skipped_no_renderer"
            return result

        rtype = getattr(renderer, "type", "")
        if rtype == "UniqueValueRenderer":
            for grp in getattr(renderer, "groups", []):
                for item in getattr(grp, "items", []):
                    label = (getattr(item, "label", "") or "").lower()
                    symbol = getattr(item, "symbol", None)
                    if symbol is None:
                        continue
                    # Base declutter: increase transparency on fills.
                    try:
                        color = dict(symbol.color)
                        if "RGB" in color and len(color["RGB"]) >= 3:
                            # Avoid blue+red overlap reading as purple on the map.
                            # Use teal for non-red classes; keep red for confidence hot spots.
                            rgb = [0, 176, 160]
                            alpha = 74
                            if "not significant" in label:
                                rgb = [0, 176, 160]
                                alpha = 68
                            elif "99%" in label:
                                rgb = [176, 0, 0]
                                alpha = 96
                                try:
                                    symbol.outlineColor = {"RGB": [255, 255, 255, 100]}
                                    symbol.outlineWidth = 1.4
                                except Exception:
                                    pass
                            if "95%" in label:
                                # Make 95% ring/fill easier to see.
                                rgb = [255, 0, 0]
                                alpha = 92
                                try:
                                    symbol.outlineColor = {"RGB": [255, 255, 255, 100]}
                                    symbol.outlineWidth = 1.4
                                except Exception:
                                    pass
                            color["RGB"] = [rgb[0], rgb[1], rgb[2], alpha]
                            symbol.color = color
                            result["updates"].append(f"updated_color:{getattr(item, 'label', '')}")
                    except Exception:
                        continue
            hotspot.symbology = sym
            if not result["updates"] and hasattr(hotspot, "transparency"):
                hotspot.transparency = 68
                result["updates"].append("layer_transparency=68")
                result["status"] = "applied_fallback_transparency"
                return result
            result["status"] = "applied"
            return result

        # Fallback for other renderer types: apply global transparency only.
        try:
            if hasattr(hotspot, "transparency"):
                hotspot.transparency = 68
                result["updates"].append("layer_transparency=68")
                result["status"] = "applied_fallback_transparency"
                return result
        except Exception:
            pass

        result["status"] = f"skipped_renderer_{rtype}"
        return result
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def harden_intervention_zone_visuals(map_obj) -> dict:
    """
    Make intervention circles less opaque and red layer easier to read.
    """
    out = {"status": "not_run", "rows": []}
    candidates = [
        "T4 Priority Intervention Zones (95%+)",
        "DV_Intervention_Zones_95pct_Polygons",
    ]
    layers = []
    for nm in candidates:
        layers.extend(get_layers_by_name(map_obj, nm))
    if not layers:
        out["status"] = "missing_layer"
        return out

    for idx, lyr in enumerate(layers):
        row = {"layer": lyr.name, "status": "unchanged", "details": []}
        try:
            if hasattr(lyr, "transparency"):
                # Keep first copy most visible; any duplicate copy is deemphasized.
                lyr.transparency = 78 if idx == 0 else 88
                row["details"].append(f"transparency={lyr.transparency}")
            if lyr.supports("SYMBOLOGY"):
                sym = lyr.symbology
                renderer = getattr(sym, "renderer", None)
                if renderer is not None and getattr(renderer, "type", "") == "SimpleRenderer":
                    symbol = getattr(renderer, "symbol", None)
                    if symbol is not None:
                        try:
                            # Light yellow fill improves separation from incidents/hotspots.
                            symbol.color = {"RGB": [255, 235, 140, 90]}
                            symbol.outlineColor = {"RGB": [180, 145, 0, 100]}
                            symbol.outlineWidth = 1.2
                            row["details"].append("simple_renderer_light_yellow")
                        except Exception:
                            pass
                    lyr.symbology = sym
            row["status"] = "applied"
        except Exception as exc:
            row["status"] = "failed"
            row["details"].append(f"{type(exc).__name__}: {exc}")
        out["rows"].append(row)

    out["status"] = "applied"
    return out


def enforce_operational_layer_hygiene(map_obj) -> list[dict]:
    """
    Keep only operational T4 layer names visible; hide raw duplicate DV layers.
    """
    results: list[dict] = []
    raw_to_operational = {
        "DV_Hotspot_Analysis": "T4 Persistent Hotspots (Top 50)",
        "DV_Intervention_Zones_95pct_Polygons": "T4 Priority Intervention Zones (95%+)",
        "DV_Incidents_Exclude_HPD_HQ": "T4 Community-Reported Incidents",
        "DV_Incidents_Within_City": "T4 Incidents Within City (Reference)",
    }
    for raw_name, operational_name in raw_to_operational.items():
        raw_layers = get_layers_by_name(map_obj, raw_name)
        op_layers = get_layers_by_name(map_obj, operational_name)
        # If both exist, hide raw. If duplicates exist, keep first visible only.
        for idx, lyr in enumerate(op_layers):
            ok = set_layer_visibility(lyr, idx == 0)
            results.append(
                {
                    "layer": lyr.name,
                    "action": "set_visible" if ok else "set_visible_failed",
                    "value": bool(idx == 0),
                }
            )
        if op_layers:
            for lyr in raw_layers:
                ok = set_layer_visibility(lyr, False)
                results.append(
                    {
                        "layer": lyr.name,
                        "action": "hide_raw_duplicate" if ok else "hide_raw_duplicate_failed",
                        "value": False,
                    }
                )
        else:
            # If operational layer doesn't exist yet, keep raw visible.
            for lyr in raw_layers:
                ok = set_layer_visibility(lyr, True)
                results.append(
                    {
                        "layer": lyr.name,
                        "action": "keep_raw_visible" if ok else "keep_raw_visible_failed",
                        "value": True,
                    }
                )

    # Collapse near-duplicate operational variants (same prefix from manual edits).
    for pref in [
        "T4 Priority Intervention Zones (95%+)",
        "T4 Persistent Hotspots (Top 50)",
    ]:
        pref_layers = get_layers_by_prefix(map_obj, pref)
        for idx, lyr in enumerate(pref_layers):
            ok = set_layer_visibility(lyr, idx == 0)
            results.append(
                {
                    "layer": lyr.name,
                    "action": "collapse_prefix_duplicates" if ok else "collapse_prefix_duplicates_failed",
                    "value": bool(idx == 0),
                }
            )
    return results


def configure_offset_layers(map_obj) -> list[dict]:
    """
    Keep one subtle offset layer for visual separation, hide extra copies.
    """
    rows: list[dict] = []
    shadow = get_layer(map_obj, "T4 Priority Intervention Zones (95%+)__Shadow")
    peel = get_layer(map_obj, "T4 Priority Intervention Zones (95%+)__Peel")

    if shadow is not None:
        vis_ok = set_layer_visibility(shadow, True)
        row = {
            "layer": shadow.name,
            "action": "offset_shadow_enable",
            "visible": True,
            "status": "applied" if vis_ok else "visibility_failed",
        }
        try:
            if hasattr(shadow, "transparency"):
                shadow.transparency = 90
                row["transparency"] = 90
            if shadow.supports("SYMBOLOGY"):
                sym = shadow.symbology
                renderer = getattr(sym, "renderer", None)
                if renderer is not None and getattr(renderer, "type", "") == "SimpleRenderer":
                    symbol = getattr(renderer, "symbol", None)
                    if symbol is not None:
                        # Force neutral gray shadow so overlap does not read as purple.
                        symbol.color = {"RGB": [190, 190, 190, 72]}
                        try:
                            # Prefer no outline for a soft ghost ring.
                            symbol.outlineColor = {"RGB": [190, 190, 190, 0]}
                            symbol.outlineWidth = 0.0
                        except Exception:
                            pass
                        row["symbol"] = "gray_shadow"
                    shadow.symbology = sym
        except Exception as exc:
            row["status"] = f"failed:{type(exc).__name__}"
        rows.append(row)

    if peel is not None:
        vis_ok = set_layer_visibility(peel, False)
        rows.append(
            {
                "layer": peel.name,
                "action": "offset_peel_hide",
                "visible": False,
                "status": "applied" if vis_ok else "visibility_failed",
            }
        )
    return rows


def configure_dark_basemap_only(map_obj) -> list[dict]:
    """
    Keep dark basemap visuals while removing reference label overlays.
    """
    rows: list[dict] = []
    for lyr in map_obj.listLayers():
        lname = lyr.name.lower()
        is_basemap = bool(getattr(lyr, "isBasemapLayer", False))
        if not is_basemap:
            continue

        if "dark gray reference" in lname or "reference" in lname:
            ok = set_layer_visibility(lyr, False)
            rows.append(
                {
                    "layer": lyr.name,
                    "action": "hide_basemap_reference",
                    "visible": False,
                    "status": "applied" if ok else "visibility_failed",
                }
            )
            continue

        if "dark gray base" in lname:
            ok = set_layer_visibility(lyr, True)
            row = {
                "layer": lyr.name,
                "action": "keep_dark_base",
                "visible": True,
                "status": "applied" if ok else "visibility_failed",
            }
            try:
                if hasattr(lyr, "transparency"):
                    lyr.transparency = 0
                    row["transparency"] = 0
            except Exception:
                pass
            rows.append(row)
    return rows


def build_style_lookup() -> dict[str, str]:
    """
    Build source layer -> style filename mapping from extraction inventory.
    """
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


def copy_labels_and_query(source_layer, target_layer) -> dict:
    copied = {
        "definition_query_copied": False,
        "labels_copied": False,
        "label_class_count": 0,
    }

    if source_layer.supports("DEFINITIONQUERY") and target_layer.supports("DEFINITIONQUERY"):
        target_layer.definitionQuery = source_layer.definitionQuery
        copied["definition_query_copied"] = True

    if source_layer.supports("SHOWLABELS") and target_layer.supports("SHOWLABELS"):
        # Some ArcPy builds do not support supports("LISTLABELCLASSES"),
        # but listLabelClasses() may still exist.
        try:
            src_classes = source_layer.listLabelClasses()
            tgt_classes = target_layer.listLabelClasses()
            # Match by order for speed in this MVP+ pass.
            for idx, src_lc in enumerate(src_classes):
                if idx < len(tgt_classes):
                    tgt_lc = tgt_classes[idx]
                    tgt_lc.expression = src_lc.expression
                    tgt_lc.SQLQuery = src_lc.SQLQuery
                    tgt_lc.visible = src_lc.visible
            target_layer.showLabels = source_layer.showLabels
            copied["labels_copied"] = True
            copied["label_class_count"] = len(src_classes)
        except Exception:
            # Keep run moving; labels can be deferred if unsupported.
            pass

    return copied


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

        result_rows = []
        for source_name, target_candidates in LAYER_MAPPING.items():
            target_name = target_candidates[0]
            style_file = style_lookup.get(source_name, f"{source_name}.lyrx")
            style_path = STYLE_DIR / style_file
            if not style_path.exists():
                result_rows.append(
                    {
                        "source_layer": source_name,
                        "target_layer": target_name,
                        "status": "skipped_missing_style_file",
                        "style_file": str(style_path),
                    }
                )
                continue

            target_layer = get_layer_by_candidates(target_map, target_candidates)
            if target_layer is None:
                result_rows.append(
                    {
                        "source_layer": source_name,
                        "target_layer": target_name,
                        "status": "skipped_missing_target_layer",
                        "style_file": str(style_path),
                    }
                )
                continue

            copied = {
                "definition_query_copied": False,
                "labels_copied": False,
                "label_class_count": 0,
            }
            style_loaded_for_label_copy = None
            try:
                # Path-based apply is more tolerant across sessions than LayerFile().
                arcpy.management.ApplySymbologyFromLayer(target_layer, str(style_path))
                try:
                    style_layers = arcpy.mp.LayerFile(str(style_path)).listLayers()
                    if style_layers:
                        style_loaded_for_label_copy = style_layers[0]
                except Exception:
                    style_loaded_for_label_copy = None
                if style_loaded_for_label_copy is not None:
                    copied = copy_labels_and_query(style_loaded_for_label_copy, target_layer)
                elif source_name in source_layer_lookup:
                    copied = copy_labels_and_query(source_layer_lookup[source_name], target_layer)
                status = "applied"
                error_msg = ""
            except Exception as exc:
                # Fallback: direct symbology + labels/query transfer from source APRX layer.
                if source_name in source_layer_lookup:
                    try:
                        src_lyr = source_layer_lookup[source_name]
                        if src_lyr.supports("SYMBOLOGY") and target_layer.supports("SYMBOLOGY"):
                            try:
                                target_layer.symbology = src_lyr.symbology
                            except Exception:
                                pass
                        copied = copy_labels_and_query(src_lyr, target_layer)
                        status = "applied_from_source_layer_fallback"
                        error_msg = f"lyrx load/apply failed, fallback used: {type(exc).__name__}: {exc}"
                    except Exception as fb_exc:
                        status = "skipped_invalid_style_file"
                        error_msg = f"{type(exc).__name__}: {exc}; fallback_failed: {type(fb_exc).__name__}: {fb_exc}"
                else:
                    status = "skipped_invalid_style_file"
                    error_msg = f"{type(exc).__name__}: {exc}"

            row = {
                "source_layer": source_name,
                "target_layer": target_name,
                "status": status,
                "style_file": str(style_path),
                **copied,
            }
            if error_msg:
                row["error"] = error_msg
            result_rows.append(row)
            if status == "applied":
                log(f"[OK] Applied style {source_name} -> {target_name}")
            else:
                log(f"[WARN] Could not apply style {source_name} -> {target_name}: {error_msg}")

        rename_rows = []
        for old_name, new_name in TARGET_RENAME_MAP.items():
            lyr = get_layer(target_map, old_name)
            if lyr is None:
                rename_rows.append({"old_name": old_name, "new_name": new_name, "status": "missing"})
                continue
            try:
                lyr.name = new_name
                rename_rows.append({"old_name": old_name, "new_name": new_name, "status": "renamed"})
                log(f"[OK] Renamed layer '{old_name}' -> '{new_name}'")
            except Exception as exc:
                rename_rows.append(
                    {
                        "old_name": old_name,
                        "new_name": new_name,
                        "status": "rename_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                log(f"[WARN] Rename failed '{old_name}' -> '{new_name}': {exc}")

        pane_hygiene_rows = enforce_operational_layer_hygiene(target_map)
        hotspot_visual_polish = harden_hotspot_visuals(target_map)
        transparency_rows = apply_layer_transparency_rules(target_map)
        offset_rows = configure_offset_layers(target_map)
        basemap_rows = configure_dark_basemap_only(target_map)

        save_status = "saved"
        save_error = ""
        try:
            aprx.save()
        except Exception as exc:
            # Common in CURRENT/OneDrive lock scenarios; style edits are often
            # already reflected in-session even when explicit save fails.
            save_status = "save_failed"
            save_error = f"{type(exc).__name__}: {exc}"
            log(f"[WARN] APRX save failed; continuing with summary output -> {save_error}")
        summary = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "target_aprx": target_aprx_ref,
            "target_map_name": TARGET_MAP_NAME,
            "save_status": save_status,
            "save_error": save_error,
            "result_rows": result_rows,
            "rename_rows": rename_rows,
            "pane_hygiene_rows": pane_hygiene_rows,
            "hotspot_visual_polish": hotspot_visual_polish,
            "transparency_rows": transparency_rows,
            "offset_rows": offset_rows,
            "basemap_rows": basemap_rows,
            "intervention_visual_polish": harden_intervention_zone_visuals(target_map),
        }
        APPLY_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        log(f"[OK] Apply summary written: {APPLY_SUMMARY}")
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
        raise
    except Exception as exc:
        print(f"Python error: {exc}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
