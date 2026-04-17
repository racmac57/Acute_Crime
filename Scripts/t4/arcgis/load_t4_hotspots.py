"""
load_t4_hotspots.py
===================
Geocodes T4_persistent_hotspots_citywide.csv, creates a point feature
class in the project GDB, adds it to the T4_2026_ArcGIS map, and applies
graduated-color symbology by persistent_risk_score with deployment-window labels.

Source: Docs/deliverables/T4_persistent_hotspots_citywide.csv
        (10 persistent hotspot locations, multi-cycle analysis)

Run from the ArcGIS Pro Python window (recommended):

    exec(open(r"C:\\Users\\carucci_r\\OneDrive - City of Hackensack\\10_Projects"
              r"\\Acute_Crime\\Scripts\\t4\\arcgis\\load_t4_hotspots.py").read())

Or from the ArcGIS Pro conda prompt:
    python "C:\\Users\\carucci_r\\...\\Scripts\\t4\\arcgis\\load_t4_hotspots.py"

Geocode strategy
----------------
Primary:  arcpy.geocoding.GeocodeAddresses() (batch, World Geocoder).
Fallback: urllib REST findAddressCandidates per address — no credits, works
          without Portal sign-in. Used automatically if batch geocoder fails.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import traceback
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import arcpy

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime"
)

APRX_PATH = (
    PROJECT_ROOT
    / "T4_2026_ArcGIS" / "T4_2026_ArcGIS" / "T4_2026_ArcGIS.aprx"
)

PROJECT_GDB = (
    PROJECT_ROOT
    / "T4_2026_ArcGIS" / "T4_2026_ArcGIS" / "T4_2026_ArcGIS.gdb"
)

CSV_PATH = (
    PROJECT_ROOT
    / "Docs" / "deliverables" / "T4_persistent_hotspots_citywide.csv"
)

TARGET_MAP_NAME = "T4_2026_ArcGIS"
FC_NAME         = "T4_Persistent_Hotspots"
LAYER_NAME      = "T4 Persistent Hotspots (All Cycles)"

OUT_DIR = PROJECT_ROOT / "_overnight" / "arcgis_style_transfer"

GEOCODE_REST = (
    "https://geocode.arcgis.com/arcgis/rest/services/World/"
    "GeocodeServer/findAddressCandidates"
)
WORLD_GEOCODER = (
    "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer"
)

# Hackensack bounding box for coordinate sanity check
HACKENSACK_BBOX = {
    "xmin": -74.09, "xmax": -74.02,
    "ymin":  40.86,  "ymax":  40.92,
}

# Graduated color ramp by risk score bucket (high → low = dark red → pale yellow)
# Applied as 5-class manual breaks on persistent_risk_score
RISK_BREAKS = [
    # (upper_bound, label,               RGBA)
    (0.50, "Risk < 0.50",           [255, 255, 178, 255]),
    (0.60, "Risk 0.50 – 0.60",      [254, 204,  92, 255]),
    (0.70, "Risk 0.60 – 0.70",      [253, 141,  60, 255]),
    (0.85, "Risk 0.70 – 0.85",      [240,  59,  32, 255]),
    (1.00, "Risk > 0.85",           [189,   0,  38, 255]),
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(msg)
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def geocode_address_rest(single_line: str) -> tuple[float, float] | None:
    """Call findAddressCandidates for one address; return (lon, lat) or None."""
    params = urllib.parse.urlencode({
        "SingleLine":   single_line,
        "outFields":    "Match_addr",
        "maxLocations": 1,
        "f":            "json",
    })
    try:
        with urllib.request.urlopen(f"{GEOCODE_REST}?{params}", timeout=15) as r:
            data = json.loads(r.read())
        candidates = data.get("candidates", [])
        if not candidates:
            return None
        loc = candidates[0]["location"]
        x, y = float(loc["x"]), float(loc["y"])
        bb = HACKENSACK_BBOX
        if not (bb["xmin"] <= x <= bb["xmax"] and bb["ymin"] <= y <= bb["ymax"]):
            log(f"  [WARN] Result outside Hackensack bbox for '{single_line}': ({x:.5f},{y:.5f})")
        return x, y
    except Exception as exc:
        log(f"  [WARN] REST geocode failed for '{single_line}': {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE CLASS SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

# (field_name, type, alias, length)
FC_FIELDS = [
    ("location_key",              "TEXT",   "Location Key",                    100),
    ("location_display",          "TEXT",   "Location",                        100),
    ("persistent_risk_score",     "DOUBLE", "Persistent Risk Score",           None),
    ("total_incidents",           "SHORT",  "Total Incidents",                 None),
    ("active_weeks",              "SHORT",  "Active Weeks",                    None),
    ("active_months",             "SHORT",  "Active Months",                   None),
    ("recency_wtd_incidents",     "DOUBLE", "Recency-Weighted Incidents",      None),
    ("severity_wtd_incidents",    "DOUBLE", "Severity-Weighted Incidents",     None),
    ("trend_90d",                 "TEXT",   "90-Day Trend",                    20),
    ("weekend_share",             "DOUBLE", "Weekend Share",                   None),
    ("weekday_share",             "DOUBLE", "Weekday Share",                   None),
    ("top_dow_1",                 "TEXT",   "Top Day of Week 1",               10),
    ("top_dow_1_share",           "DOUBLE", "Top DOW 1 Share",                 None),
    ("top_dow_2",                 "TEXT",   "Top Day of Week 2",               10),
    ("top_dow_2_share",           "DOUBLE", "Top DOW 2 Share",                 None),
    ("top_time_window_1",         "TEXT",   "Top Time Window 1",               30),
    ("top_time_window_1_share",   "DOUBLE", "Top Time Window 1 Share",         None),
    ("top_time_window_2",         "TEXT",   "Top Time Window 2",               30),
    ("top_time_window_2_share",   "DOUBLE", "Top Time Window 2 Share",         None),
    ("top_dom_band",              "TEXT",   "Top Day-of-Month Band",           20),
    ("deployment_window",         "TEXT",   "Deployment Window Recommendation",100),
    ("confidence_band",           "TEXT",   "Confidence Band",                 20),
    ("geocode_addr",              "TEXT",   "Geocoded Address (Matched)",      200),
]

# CSV column → FC field name
CSV_TO_FC = {
    "location_key":                 "location_key",
    "location_display":             "location_display",
    "persistent_risk_score":        "persistent_risk_score",
    "total_incidents":              "total_incidents",
    "active_weeks_count":           "active_weeks",
    "active_months_count":          "active_months",
    "recency_weighted_incidents":   "recency_wtd_incidents",
    "severity_weighted_incidents":  "severity_wtd_incidents",
    "trend_90d":                    "trend_90d",
    "weekend_share":                "weekend_share",
    "weekday_share":                "weekday_share",
    "top_dow_1":                    "top_dow_1",
    "top_dow_1_share":              "top_dow_1_share",
    "top_dow_2":                    "top_dow_2",
    "top_dow_2_share":              "top_dow_2_share",
    "top_time_window_1":            "top_time_window_1",
    "top_time_window_1_share":      "top_time_window_1_share",
    "top_time_window_2":            "top_time_window_2",
    "top_time_window_2_share":      "top_time_window_2_share",
    "top_day_of_month_band":        "top_dom_band",
    "deployment_window_recommendation": "deployment_window",
    "confidence_band":              "confidence_band",
}

NUMERIC_FIELDS = {
    "persistent_risk_score", "total_incidents", "active_weeks", "active_months",
    "recency_wtd_incidents", "severity_wtd_incidents", "weekend_share",
    "weekday_share", "top_dow_1_share", "top_dow_2_share",
    "top_time_window_1_share", "top_time_window_2_share",
}

INT_FIELDS = {"total_incidents", "active_weeks", "active_months"}


def cast(fname: str, raw: str):
    if fname not in NUMERIC_FIELDS:
        return str(raw) if raw else ""
    if not raw:
        return None
    try:
        return int(raw) if fname in INT_FIELDS else float(raw)
    except (ValueError, TypeError):
        return None


def create_feature_class(gdb: Path, fc_name: str) -> str:
    fc_path = str(gdb / fc_name)
    if arcpy.Exists(fc_path):
        arcpy.management.Delete(fc_path)
        log(f"  [INFO] Deleted existing FC: {fc_name}")
    arcpy.management.CreateFeatureclass(
        out_path=str(gdb),
        out_name=fc_name,
        geometry_type="POINT",
        spatial_reference=arcpy.SpatialReference(4326),
    )
    for fname, ftype, falias, flen in FC_FIELDS:
        if ftype == "TEXT" and flen:
            arcpy.management.AddField(fc_path, fname, ftype, field_alias=falias, field_length=flen)
        else:
            arcpy.management.AddField(fc_path, fname, ftype, field_alias=falias)
    log(f"  [OK] Feature class created: {fc_path}")
    return fc_path


def insert_rows(fc_path: str, geocoded: list[dict]) -> int:
    fc_field_names = [f[0] for f in FC_FIELDS]
    insert_fields  = ["SHAPE@XY"] + fc_field_names
    fc_to_csv = {v: k for k, v in CSV_TO_FC.items()}
    inserted = 0
    with arcpy.da.InsertCursor(fc_path, insert_fields) as cur:
        for rec in geocoded:
            row_csv = rec["csv"]
            vals = [(rec["lon"], rec["lat"])]
            for fname, *_ in FC_FIELDS:
                if fname == "geocode_addr":
                    vals.append(rec.get("geocode_addr", ""))
                else:
                    csv_key = fc_to_csv.get(fname)
                    raw = row_csv.get(csv_key, "") if csv_key else ""
                    vals.append(cast(fname, raw))
            cur.insertRow(vals)
            inserted += 1
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# SYMBOLOGY
# ─────────────────────────────────────────────────────────────────────────────

def apply_symbology(lyr) -> str:
    """Graduated color by persistent_risk_score (5-class manual breaks) + deployment-window labels."""
    status = "not_run"
    try:
        if not lyr.supports("SYMBOLOGY"):
            return "skipped_no_symbology"

        sym = lyr.symbology
        sym.updateRenderer("GraduatedColorsRenderer")
        sym.renderer.classificationField = "persistent_risk_score"
        sym.renderer.breakCount = len(RISK_BREAKS)

        # Apply manual break values and colors
        for idx, (upper, label, rgba) in enumerate(RISK_BREAKS):
            brk = sym.renderer.classBreaks[idx]
            brk.upperBound = upper
            brk.label      = label
            brk.symbol.color        = {"RGB": rgba}
            brk.symbol.outlineColor = {"RGB": [50, 50, 50, 200]}
            brk.symbol.outlineWidth = 0.6
            # Larger symbol for higher risk
            brk.symbol.size = 8 + (idx * 2)   # 8, 10, 12, 14, 16 pt

        lyr.symbology = sym
        status = "applied_graduated_color"
    except Exception as exc:
        status = f"failed:{type(exc).__name__}: {exc}"

    # Labels: show location_display on one line, deployment_window on second line
    try:
        if lyr.supports("SHOWLABELS"):
            lyr.showLabels = True
            for lc in lyr.listLabelClasses():
                lc.expression = (
                    "$feature.location_display + TextFormatting.NewLine + "
                    "'[' + $feature.deployment_window + ']'"
                )
                lc.expressionEngine = "Arcade"
                lc.visible = True
    except Exception:
        pass

    return status


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    arcpy.env.overwriteOutput = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log(f"\n{'='*60}")
    log(f"T4 Persistent Hotspots — Geocode + Load  |  {datetime.now():%Y-%m-%d %H:%M}")
    log(f"{'='*60}")

    if not CSV_PATH.exists():
        log(f"[ERROR] CSV not found: {CSV_PATH}")
        sys.exit(1)

    rows = read_csv(CSV_PATH)
    log(f"[INFO] {len(rows)} rows loaded from {CSV_PATH.name}")

    # ── Geocode ───────────────────────────────────────────────────────────────
    log("\n── Geocoding addresses ──")
    geocoded: list[dict] = []
    failed:   list[str]  = []

    # Build SingleLine addresses (block-level + city/state/zip)
    for row in rows:
        row["_single_line"] = f"{row['location_display']}, Hackensack, NJ, 07601"

    # Attempt batch geocoder
    batch_success = False
    try:
        log("  [INFO] Trying batch geocoder (World Geocoder)…")

        # Write temp CSV with SingleLine column for batch geocoder
        import tempfile
        tmp_csv = Path(tempfile.mktemp(suffix=".csv"))
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["location_key", "SingleLine"])
            w.writeheader()
            for row in rows:
                w.writerow({"location_key": row["location_key"],
                            "SingleLine":   row["_single_line"]})

        temp_fc = str(PROJECT_GDB / f"{FC_NAME}_geocode_temp")
        arcpy.geocoding.GeocodeAddresses(
            in_table=str(tmp_csv),
            address_locator=WORLD_GEOCODER,
            in_address_fields=[["SingleLine", "SingleLine"]],
            out_feature_class=temp_fc,
        )
        tmp_csv.unlink(missing_ok=True)

        addr_lookup: dict[str, tuple] = {}
        with arcpy.da.SearchCursor(
            temp_fc, ["SHAPE@XY", "USER_SingleLine", "Match_addr", "Status"]
        ) as cur:
            for xy, single, match, status in cur:
                if status == "M" and xy:
                    addr_lookup[single.strip()] = (xy[0], xy[1], match or single)

        for row in rows:
            key = row["_single_line"].strip()
            if key in addr_lookup:
                lon, lat, matched = addr_lookup[key]
                geocoded.append({"csv": row, "lon": lon, "lat": lat, "geocode_addr": matched})
                log(f"  [OK] {row['location_display']} → ({lon:.5f}, {lat:.5f})")
            else:
                log(f"  [WARN] No match: {key}")
                failed.append(row["_single_line"])

        if arcpy.Exists(temp_fc):
            arcpy.management.Delete(temp_fc)
        batch_success = True
        log(f"  [INFO] Batch: {len(geocoded)} matched, {len(failed)} failed.")
    except Exception as exc:
        log(f"  [WARN] Batch geocoder failed ({type(exc).__name__}: {exc}) — using REST fallback.")

    # REST fallback for misses (or all rows if batch failed)
    fallback_rows = rows if not batch_success else [
        r for r in rows if r["_single_line"] in failed
    ]
    for row in fallback_rows:
        addr   = row["_single_line"]
        result = geocode_address_rest(addr)
        if result:
            lon, lat = result
            geocoded.append({"csv": row, "lon": lon, "lat": lat, "geocode_addr": addr})
            log(f"  [OK-REST] {row['location_display']} → ({lon:.5f}, {lat:.5f})")
        else:
            log(f"  [FAIL] Could not geocode: {addr}")

    if not geocoded:
        log("[ERROR] No addresses geocoded. Check network/Portal sign-in.")
        sys.exit(1)

    log(f"\n[INFO] {len(geocoded)}/{len(rows)} addresses geocoded.")

    # ── Build feature class ───────────────────────────────────────────────────
    log("\n── Creating feature class ──")
    if not PROJECT_GDB.exists():
        log(f"  [INFO] Creating project GDB: {PROJECT_GDB}")
        arcpy.management.CreateFileGDB(str(PROJECT_GDB.parent), PROJECT_GDB.name)

    fc_path  = create_feature_class(PROJECT_GDB, FC_NAME)
    inserted = insert_rows(fc_path, geocoded)
    log(f"  [OK] {inserted} rows inserted into {FC_NAME}.")

    # ── Add to map + symbolize ────────────────────────────────────────────────
    log("\n── Adding to map ──")
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        log("  [INFO] Using currently open project.")
    except Exception:
        if not APRX_PATH.exists():
            log(f"  [ERROR] APRX not found: {APRX_PATH}")
            sys.exit(1)
        aprx = arcpy.mp.ArcGISProject(str(APRX_PATH))
        log(f"  [INFO] Opened: {APRX_PATH}")

    all_maps    = aprx.listMaps()
    target_map  = next((m for m in all_maps if m.name == TARGET_MAP_NAME), None)
    if target_map is None:
        target_map = all_maps[0]
        log(f"  [WARN] Map '{TARGET_MAP_NAME}' not found — using '{target_map.name}'.")

    for lyr in target_map.listLayers():
        if lyr.name == LAYER_NAME:
            target_map.removeLayer(lyr)
            log(f"  [INFO] Removed existing layer '{LAYER_NAME}'.")
            break

    added_lyr      = target_map.addDataFromPath(fc_path)
    added_lyr.name = LAYER_NAME
    log(f"  [OK] Layer added: '{LAYER_NAME}'")

    sym_status = apply_symbology(added_lyr)
    log(f"  [INFO] Symbology: {sym_status}")

    # ── Save ──────────────────────────────────────────────────────────────────
    save_status = "saved"
    try:
        aprx.save()
        log("\n[OK] Project saved.")
    except Exception as exc:
        save_status = f"save_failed: {exc}"
        log(f"\n[WARN] Auto-save failed — use File > Save in ArcGIS Pro. ({exc})")

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = {
        "run_at":      datetime.now().isoformat(timespec="seconds"),
        "csv":         str(CSV_PATH),
        "csv_rows":    len(rows),
        "geocoded":    len(geocoded),
        "failed":      len(rows) - len(geocoded),
        "fc_path":     fc_path,
        "layer_name":  LAYER_NAME,
        "symbology":   sym_status,
        "save_status": save_status,
        "points": [
            {
                "location":    r["csv"]["location_display"],
                "risk":        float(r["csv"]["persistent_risk_score"]),
                "confidence":  r["csv"]["confidence_band"],
                "window":      r["csv"]["deployment_window_recommendation"],
                "lon":         round(r["lon"], 6),
                "lat":         round(r["lat"], 6),
            }
            for r in geocoded
        ],
    }
    summary_path = OUT_DIR / "load_t4_hotspots_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"[OK] Summary: {summary_path}")

    log("\n── Hotspot Points Loaded ──")
    for i, pt in enumerate(summary["points"], 1):
        log(f"  {i:2d}. {pt['location']:<30s} risk={pt['risk']:.4f}  [{pt['window']}]")

    log(f"\n{'='*60}")
    log(f"DONE — {len(geocoded)} persistent hotspot(s) loaded into '{LAYER_NAME}'")
    log(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
        traceback.print_exc()
        raise
    except Exception as exc:
        print(f"Python error: {exc}")
        traceback.print_exc()
        raise
