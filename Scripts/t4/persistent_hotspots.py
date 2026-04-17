"""
T4 Persistent Hotspots — strategic patrol allocation product.

Builds a location-level persistence model using CAD + RMS from 2024-01-01
through 2026-03-31, focused on group/fight-relevant incidents. Applies the
existing T4 DV exclusion (Layer 1 blocklist + Layer 2 type fallback) to RMS,
computes frequency / persistence / recency / severity components, combines
into a composite persistent_risk_score, and produces temporal patterns
(DOW / time-of-day / day-of-month) with a deployment-window recommendation.

Outputs (repo-approved paths only):
    Docs/deliverables/T4_persistent_hotspots_citywide.csv
    Docs/deliverables/T4_persistent_hotspots_command_staff.md
    Docs/deliverables/T4_persistent_hotspots_technical_appendix.md
    _overnight/persistent_hotspots/<intermediate artifacts>

Evidence-based risk patterning — NOT deterministic prediction.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from Scripts.t4.column_norm import normalize_columns, standardize_case_number
from Scripts.t4.type_fallback import build_dv_type_set, flag_dv_by_type

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ONEDRIVE = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack")
PROJECT = ONEDRIVE / "10_Projects" / "Acute_Crime"

PATHS = {
    "dv_blocklist":        PROJECT / "Data" / "dv_case_numbers_for_t4.csv",
    "incident_type_map":   ONEDRIVE / "02_ETL_Scripts" / "dv_doj" / "docs" / "mappings" / "incident_type_map.csv",
    "calltype_categories": ONEDRIVE / "09_Reference" / "Classifications" / "CallTypes" / "CallType_Categories.csv",
    "cad_monthly":         PROJECT / "Data" / "cad" / "monthly",
    "cad_yearly":          PROJECT / "Data" / "cad" / "yearly",
    "rms_monthly":         PROJECT / "Data" / "rms" / "monthly",
    "rms_yearly":          PROJECT / "Data" / "rms" / "yearly",
    "deliverables":        PROJECT / "Docs" / "deliverables",
    "overnight":           PROJECT / "_overnight" / "persistent_hotspots",
}

HORIZON_START = pd.Timestamp("2024-01-01")
HORIZON_END   = pd.Timestamp("2026-03-31 23:59:59")
ANALYSIS_DATE = pd.Timestamp("2026-03-31")

# ── Group/fight-relevant CAD inclusion (severity-weighted) ────────────────
# Ordered: earlier patterns win. Each tuple (substring_lower, severity_points).
# Severity mirrors T4 Tier 1 conventions plus light extension for disturbance.
CAD_SEVERITY_RULES: list[tuple[str, int]] = [
    ("shots fired",          5),
    ("weapons seizure",      5),
    ("weapon",               5),
    ("aggravated assault",   4),
    ("fight - armed",        4),
    ("fight -armed",         4),
    ("fight armed",          4),
    ("fight - unarmed",      3),
    ("fight -unarmed",       3),
    ("fight unarmed",        3),
    ("fight",                3),
    ("brawl",                3),
    ("group fight",          3),
    ("disorderly group",     3),
    ("simple assault",       3),
    ("sexual assault",       4),  # severity only; DV filter handled separately in RMS
    ("disturbance",          2),
    ("suspicious person",    2),
    ("suspicious vehicle",   2),
    ("suspicious incident",  2),
    ("suspicious activity",  2),
    ("suspicious item",      2),
    ("suspicious",           2),
    ("group",                3),  # catches 'Group', 'group\n', 'GROUP'
]

# RMS Part 1 severity (group/fight-relevant): Tier-2 bonus style
RMS_SEVERITY_BY_NIBRS = {
    "09A": 10, "09B": 10,   # Homicide / Neg. Manslaughter
    "120":  7,              # Robbery (weighted high regardless of weapon subtype)
    "13A":  5,              # Aggravated Assault (RMS-confirmed)
    "13B":  3,              # Simple Assault
    "13C":  2,              # Intimidation
    "220":  3,              # Burglary
    "240":  2,              # Motor Vehicle Theft
}

# Time-of-day bins (master-prompt §11)
TOD_BINS = [
    ("Early Morning 00-03", 0,  4),
    ("Morning 04-07",       4,  8),
    ("Morning Peak 08-11",  8, 12),
    ("Afternoon 12-15",    12, 16),
    ("Evening Peak 16-19", 16, 20),
    ("Night 20-23",        20, 24),
]

DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Excluded dispositions + HowReported values (self-initiated, etc.)
EXCLUDED_DISPOSITIONS = {"unfounded", "canceled", "cancelled", "checked ok"}


# ── Helpers ────────────────────────────────────────────────────────────────
def nibrs_prefix(raw) -> str:
    if pd.isna(raw):
        return ""
    s = str(raw).strip().upper()
    m = re.match(r"^(\d{2}[A-Z]|\d{3})\b", s)
    return m.group(1) if m else ""


def cad_severity(incident) -> int:
    if pd.isna(incident):
        return 0
    s = str(incident).strip().lower()
    for pat, pts in CAD_SEVERITY_RULES:
        if pat in s:
            return pts
    return 0


def recency_multiplier(event_date: pd.Timestamp, analysis_date: pd.Timestamp) -> float:
    if pd.isna(event_date):
        return 0.0
    days = (analysis_date - event_date).days
    if days <= 28:
        return 1.00
    if days <= 90:
        return 0.75
    if days <= 180:
        return 0.50
    return 0.25


def tod_bin(hour) -> str:
    if pd.isna(hour):
        return "Unknown"
    h = int(hour)
    for label, lo, hi in TOD_BINS:
        if lo <= h < hi:
            return label
    return "Unknown"


def dom_band(day) -> str:
    if pd.isna(day):
        return "Unknown"
    d = int(day)
    if d <= 10:
        return "early (1-10)"
    if d <= 20:
        return "mid (11-20)"
    return "late (21-31)"


# ── Address normalization ──────────────────────────────────────────────────
_SUFFIX_MAP = {
    r"\bSt\.?\b":   "St",  r"\bStreet\b": "St",
    r"\bAve\.?\b":  "Ave", r"\bAvenue\b": "Ave",
    r"\bPl\.?\b":   "Pl",  r"\bPlace\b":  "Pl",
    r"\bBlvd\.?\b": "Blvd", r"\bBoulevard\b": "Blvd",
    r"\bRd\.?\b":   "Rd",  r"\bRoad\b":   "Rd",
    r"\bDr\.?\b":   "Dr",  r"\bDrive\b":  "Dr",
    r"\bCt\.?\b":   "Ct",  r"\bCourt\b":  "Ct",
    r"\bLn\.?\b":   "Ln",  r"\bLane\b":   "Ln",
    r"\bTer\.?\b":  "Ter", r"\bTerrace\b":"Ter",
    r"\bPkwy\.?\b": "Pkwy",r"\bParkway\b":"Pkwy",
    r"\bHwy\.?\b":  "Hwy", r"\bHighway\b":"Hwy",
}
_HACK_TRAIL = re.compile(r",?\s*Hackensack,?\s*NJ[,\s]*\d{0,5}\s*$", re.IGNORECASE)
_APT_RE = re.compile(r"\b(?:apt\.?|unit|suite|ste\.?|#)\s*[\w-]+", re.IGNORECASE)


def _standardize_suffix(s: str) -> str:
    for pat, rep in _SUFFIX_MAP.items():
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)
    return s


def normalize_address(raw) -> tuple[str, str]:
    """
    Return (location_key, location_display).
    - location_key: canonical lowercase key used for grouping
    - location_display: human-readable ("100 Block Main St" or "Main St & 1st St")
    """
    if pd.isna(raw) or not str(raw).strip():
        return "", ""
    s = str(raw).strip()
    s = s.lstrip(",&").strip()
    s = _HACK_TRAIL.sub("", s).strip(" ,")
    s = _APT_RE.sub("", s).strip(" ,")
    s = re.sub(r"\s+", " ", s)
    s = _standardize_suffix(s)

    # Intersection form
    if "&" in s:
        parts = [p.strip(" ,") for p in s.split("&") if p.strip(" ,")]
        parts = sorted(parts, key=str.lower)
        display = " & ".join(parts)
        key = display.lower()
        return key, display

    # Street-segment form: leading house number → 100 Block
    m = re.match(r"^(\d+)\s+(.+)$", s)
    if m:
        num = int(m.group(1))
        street = m.group(2).strip(" ,")
        if not street:
            return "", ""
        # Bucket to 100-block hundreds (0-99 → "0 Block", etc.)
        bucket = (num // 100) * 100
        display = f"{bucket} Block {street}"
        key = display.lower()
        return key, display

    # No house number and no & — use street name as-is
    if re.match(r"^[A-Za-z].+", s):
        display = s
        return s.lower(), display

    return "", ""


# ── Data loading ───────────────────────────────────────────────────────────
def load_cad_window() -> pd.DataFrame:
    frames = []
    for folder in [PATHS["cad_yearly"], PATHS["cad_monthly"]]:
        if not folder.exists():
            continue
        for f in sorted(folder.glob("*.xlsx")):
            if f.stat().st_size == 0:
                log.warning(f"Skipping 0-byte CAD file: {f.name}")
                continue
            log.info(f"Loading CAD: {f.name}")
            df = pd.read_excel(f, dtype=str)
            df = normalize_columns(df)
            frames.append(df)
    if not frames:
        log.error("No CAD files found")
        sys.exit(1)
    cad = pd.concat(frames, ignore_index=True)
    cad = cad.drop_duplicates(subset="report_number_new")
    cad["time_of_call_parsed"] = pd.to_datetime(cad.get("time_of_call"), errors="coerce")
    cad = cad[cad["time_of_call_parsed"].notna()]
    cad = cad[(cad["time_of_call_parsed"] >= HORIZON_START) & (cad["time_of_call_parsed"] <= HORIZON_END)]
    log.info(f"CAD in horizon: {len(cad):,} rows")
    return cad


def load_rms_window() -> pd.DataFrame:
    frames = []
    for folder in [PATHS["rms_yearly"], PATHS["rms_monthly"]]:
        if not folder.exists():
            continue
        for f in sorted(folder.glob("*.xlsx")):
            if f.stat().st_size == 0:
                log.warning(f"Skipping 0-byte RMS file: {f.name}")
                continue
            log.info(f"Loading RMS: {f.name}")
            df = pd.read_excel(f, dtype=str)
            df = normalize_columns(df)
            frames.append(df)
    if not frames:
        log.error("No RMS files found")
        sys.exit(1)
    rms = pd.concat(frames, ignore_index=True)
    rms = rms.drop_duplicates(subset="case_number")
    rms["incident_date_parsed"] = pd.to_datetime(rms.get("incident_date"), errors="coerce")
    if "report_date" in rms.columns:
        rms["report_date_parsed"] = pd.to_datetime(rms.get("report_date"), errors="coerce")
        rms["incident_date_parsed"] = rms["incident_date_parsed"].fillna(rms["report_date_parsed"])
    rms = rms[rms["incident_date_parsed"].notna()]
    rms = rms[(rms["incident_date_parsed"] >= HORIZON_START) & (rms["incident_date_parsed"] <= HORIZON_END)]
    log.info(f"RMS in horizon: {len(rms):,} rows")
    return rms


def load_dv_blocklist() -> tuple[set, str]:
    p = PATHS["dv_blocklist"]
    bl = pd.read_csv(p)
    cases = set(bl["case_number"].dropna().str.strip().str.upper())
    return cases, str(bl["source_date_end"].max())


# ── DV exclusion (reuse pattern from score_integration.py) ─────────────────
def apply_dv_exclusion(rms: pd.DataFrame, dv_blocklist: set, dv_type_set: set) -> tuple[pd.DataFrame, dict]:
    total = len(rms)
    rms = rms.copy()
    rms["_cn_std"] = rms["case_number"].apply(standardize_case_number)
    layer1 = rms["_cn_std"].isin(dv_blocklist)
    layer2 = flag_dv_by_type(rms, dv_type_set) & ~layer1
    excluded = layer1 | layer2
    stats = {
        "total_rms_before_filter": total,
        "excluded_dv_case_match": int(layer1.sum()),
        "excluded_type_fallback": int(layer2.sum()),
        "total_excluded": int(excluded.sum()),
        "scoring_ready_rows": int((~excluded).sum()),
    }
    kept = rms[~excluded].drop(columns=["_cn_std"])
    log.info(f"DV exclusion → {stats}")
    return kept, stats


# ── Filter CAD to group/fight-relevant & citizen-generated ─────────────────
def prep_cad_incidents(cad: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    before = len(cad)
    cad = cad.copy()
    cad["severity"] = cad["incident"].apply(cad_severity)
    rel = cad[cad["severity"] > 0].copy()
    after_rel = len(rel)

    if "how_reported" in rel.columns:
        hr = rel["how_reported"].fillna("").str.strip().str.lower()
        citizen = ~hr.isin(["self-initiated", "self initiated"])
        rel = rel[citizen]
    after_citizen = len(rel)

    if "disposition" in rel.columns:
        disp = rel["disposition"].fillna("").str.strip().str.lower()
        rel = rel[~disp.isin(EXCLUDED_DISPOSITIONS)]
    after_disp = len(rel)

    stats = {
        "cad_total_in_horizon": before,
        "cad_group_fight_relevant": after_rel,
        "cad_after_self_init_excl": after_citizen,
        "cad_after_disposition_excl": after_disp,
    }
    log.info(f"CAD filtering → {stats}")
    return rel.reset_index(drop=True), stats


def prep_rms_incidents(rms: pd.DataFrame) -> pd.DataFrame:
    rms = rms.copy()
    rms["nibrs_prefix"] = rms.get("nibrs_classification", "").apply(nibrs_prefix)
    rms["severity"] = rms["nibrs_prefix"].map(RMS_SEVERITY_BY_NIBRS).fillna(0).astype(int)
    rms_kept = rms[rms["severity"] > 0].copy()
    return rms_kept.reset_index(drop=True)


# ── Unified incident table ────────────────────────────────────────────────
def build_unified(cad: pd.DataFrame, rms: pd.DataFrame) -> pd.DataFrame:
    c = pd.DataFrame({
        "source":        "CAD",
        "event_id":      cad["report_number_new"],
        "event_date":    cad["time_of_call_parsed"],
        "raw_address":   cad.get("full_address_2", pd.Series("", index=cad.index)),
        "severity":      cad["severity"].astype(int),
        "incident_type": cad["incident"],
    })
    r = pd.DataFrame({
        "source":        "RMS",
        "event_id":      rms["case_number"],
        "event_date":    rms["incident_date_parsed"],
        "raw_address":   rms.get("full_address", pd.Series("", index=rms.index)),
        "severity":      rms["severity"].astype(int),
        "incident_type": rms.get("nibrs_classification", ""),
    })
    all_events = pd.concat([c, r], ignore_index=True)

    # Normalize addresses
    norm = all_events["raw_address"].apply(normalize_address)
    all_events["location_key"]     = norm.apply(lambda t: t[0])
    all_events["location_display"] = norm.apply(lambda t: t[1])
    all_events = all_events[all_events["location_key"] != ""].reset_index(drop=True)

    # Temporal features
    all_events["event_date"] = pd.to_datetime(all_events["event_date"])
    all_events["iso_year"]   = all_events["event_date"].dt.isocalendar().year
    all_events["iso_week"]   = all_events["event_date"].dt.isocalendar().week
    all_events["year_week"]  = (
        all_events["iso_year"].astype(str) + "-W" +
        all_events["iso_week"].astype(str).str.zfill(2)
    )
    all_events["year_month"] = all_events["event_date"].dt.to_period("M").astype(str)
    all_events["dow_idx"]    = all_events["event_date"].dt.weekday
    all_events["dow_name"]   = all_events["dow_idx"].map(lambda i: DOW_NAMES[i] if pd.notna(i) else "Unknown")
    all_events["hour"]       = all_events["event_date"].dt.hour
    all_events["tod_bin"]    = all_events["hour"].apply(tod_bin)
    all_events["dom"]        = all_events["event_date"].dt.day
    all_events["dom_band"]   = all_events["dom"].apply(dom_band)
    all_events["is_weekend"] = all_events["dow_idx"].isin([5, 6])
    all_events["decay"]      = all_events["event_date"].apply(lambda d: recency_multiplier(d, ANALYSIS_DATE))
    all_events["severity_weighted_decay"] = all_events["severity"] * all_events["decay"]
    all_events["recency_weighted_count"]  = all_events["decay"]

    return all_events


# ── Location aggregation ──────────────────────────────────────────────────
def _top_share(series: pd.Series) -> tuple[str, float, str, float]:
    if series.empty:
        return ("", 0.0, "", 0.0)
    counts = series.value_counts(normalize=True)
    top1 = counts.index[0]; share1 = float(counts.iloc[0])
    if len(counts) >= 2:
        top2 = counts.index[1]; share2 = float(counts.iloc[1])
    else:
        top2, share2 = "", 0.0
    return (str(top1), round(share1, 3), str(top2), round(share2, 3))


def aggregate_locations(events: pd.DataFrame) -> pd.DataFrame:
    log.info(f"Aggregating {len(events):,} events to locations")
    rows = []

    # Pre-compute last-90d vs prior-90d buckets for trend
    cutoff_90 = ANALYSIS_DATE - pd.Timedelta(days=90)
    cutoff_180 = ANALYSIS_DATE - pd.Timedelta(days=180)

    for key, g in events.groupby("location_key"):
        display = g["location_display"].iloc[0]
        total = len(g)
        weeks = g["year_week"].nunique()
        months = g["year_month"].nunique()

        rec_weighted = float(g["recency_weighted_count"].sum())
        sev_weighted = float(g["severity_weighted_decay"].sum())

        last90 = int(((g["event_date"] > cutoff_90) & (g["event_date"] <= ANALYSIS_DATE)).sum())
        prior90 = int(((g["event_date"] > cutoff_180) & (g["event_date"] <= cutoff_90)).sum())
        if prior90 == 0:
            if last90 == 0:
                trend = "flat"
            else:
                trend = "up"
        else:
            ratio = last90 / prior90
            if ratio >= 1.20:
                trend = "up"
            elif ratio <= 0.80:
                trend = "down"
            else:
                trend = "flat"

        weekend = int(g["is_weekend"].sum())
        weekday = total - weekend
        weekend_share = round(weekend / total, 3) if total else 0.0
        weekday_share = round(weekday / total, 3) if total else 0.0

        dow_top1, dow_share1, dow_top2, dow_share2 = _top_share(g["dow_name"])
        tod_top1, tod_share1, tod_top2, tod_share2 = _top_share(
            g.loc[g["tod_bin"] != "Unknown", "tod_bin"]
        )
        dom_top1, _, _, _ = _top_share(g["dom_band"])

        rows.append({
            "location_key":              key,
            "location_display":          display,
            "total_incidents":           total,
            "active_weeks_count":        weeks,
            "active_months_count":       months,
            "recency_weighted_incidents":round(rec_weighted, 3),
            "severity_weighted_incidents":round(sev_weighted, 3),
            "last_90d_count":            last90,
            "prior_90d_count":           prior90,
            "trend_90d":                 trend,
            "weekend_share":             weekend_share,
            "weekday_share":             weekday_share,
            "top_dow_1":                 dow_top1,
            "top_dow_1_share":           dow_share1,
            "top_dow_2":                 dow_top2,
            "top_dow_2_share":           dow_share2,
            "top_time_window_1":         tod_top1,
            "top_time_window_1_share":   tod_share1,
            "top_time_window_2":         tod_top2,
            "top_time_window_2_share":   tod_share2,
            "top_day_of_month_band":     dom_top1,
            "cad_count":                 int((g["source"] == "CAD").sum()),
            "rms_count":                 int((g["source"] == "RMS").sum()),
            "last_incident_date":        g["event_date"].max().date().isoformat(),
        })

    return pd.DataFrame(rows)


# ── Composite scoring & confidence ────────────────────────────────────────
def _minmax(s: pd.Series) -> pd.Series:
    if s.max() == s.min():
        return pd.Series(0.0, index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def compute_composite(locs: pd.DataFrame) -> pd.DataFrame:
    locs = locs.copy()
    # Four components, min-max normalized to [0,1]
    freq_n = _minmax(locs["total_incidents"])
    pers_n = _minmax(locs["active_months_count"])
    recn_n = _minmax(locs["recency_weighted_incidents"])
    sev_n  = _minmax(locs["severity_weighted_incidents"])

    # Weighted composite. Tilt toward persistence + severity over raw frequency.
    # frequency 0.20, persistence 0.30, recency 0.20, severity 0.30
    locs["persistent_risk_score"] = (
        0.20 * freq_n + 0.30 * pers_n + 0.20 * recn_n + 0.30 * sev_n
    ).round(4)

    # Confidence band
    def conf(r):
        if r["total_incidents"] >= 20 and r["active_months_count"] >= 6 and r["active_weeks_count"] >= 10:
            return "high"
        if r["total_incidents"] >= 8 and r["active_months_count"] >= 3:
            return "medium"
        return "low"
    locs["confidence_band"] = locs.apply(conf, axis=1)

    # Deployment window recommendation string
    def rec(r):
        dow = r["top_dow_1"] or "—"
        dow2 = f"+{r['top_dow_2']}" if r["top_dow_2"] else ""
        tod = r["top_time_window_1"] or "—"
        dom = r["top_day_of_month_band"] or "—"
        return f"{dow}{dow2} / {tod} / {dom}"
    locs["deployment_window_recommendation"] = locs.apply(rec, axis=1)

    # Notes: data-quality hints
    def note(r):
        parts = []
        if r["total_incidents"] < 8:
            parts.append("low-volume location (briefing caveat)")
        if r["rms_count"] == 0:
            parts.append("CAD-only (no RMS Part 1 confirmation)")
        if r["cad_count"] == 0:
            parts.append("RMS-only (no CAD disorder signal)")
        if r["top_time_window_1_share"] == 0.0:
            parts.append("time-of-day data sparse")
        return "; ".join(parts)
    locs["notes"] = locs.apply(note, axis=1)

    return locs.sort_values("persistent_risk_score", ascending=False).reset_index(drop=True)


# ── Report writers ────────────────────────────────────────────────────────
OUTPUT_COLUMNS = [
    "location_key",
    "location_display",
    "persistent_risk_score",
    "total_incidents",
    "active_weeks_count",
    "active_months_count",
    "recency_weighted_incidents",
    "severity_weighted_incidents",
    "trend_90d",
    "weekend_share",
    "weekday_share",
    "top_dow_1",
    "top_dow_1_share",
    "top_dow_2",
    "top_dow_2_share",
    "top_time_window_1",
    "top_time_window_1_share",
    "top_time_window_2",
    "top_time_window_2_share",
    "top_day_of_month_band",
    "deployment_window_recommendation",
    "confidence_band",
    "notes",
]


def write_csv(locs: pd.DataFrame, path: Path, top_n: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    missing = [c for c in OUTPUT_COLUMNS if c not in locs.columns]
    if missing:
        raise RuntimeError(f"Schema check failed; missing columns: {missing}")
    out = locs if top_n is None else locs.head(top_n)
    out.to_csv(path, columns=OUTPUT_COLUMNS, index=False)
    log.info(f"CSV written: {path} ({len(out):,} rows)")


def write_command_staff_md(locs: pd.DataFrame, path: Path, stats: dict) -> None:
    top10 = locs.head(10)
    lines = []
    lines.append("# T4 Persistent Hotspots — Command Staff Briefing")
    lines.append("")
    lines.append(f"**Horizon:** {HORIZON_START.date()} through {HORIZON_END.date()} (analysis date {ANALYSIS_DATE.date()})")
    lines.append(f"**Scope:** group/fight/disorder-relevant CAD incidents + RMS Part 1 violent crimes at same locations")
    lines.append(f"**Classification:** Law Enforcement Sensitive. Location-based, condition-focused. No individual targeting.")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("Historical risk patterning to inform targeted patrol allocation (where + when). "
                 "This is evidence-based persistence analysis, not deterministic prediction. "
                 "Outputs are advisory — field supervisors validate ground truth before deployment decisions.")
    lines.append("")
    lines.append("## Top 10 Persistent Hotspots")
    lines.append("")
    lines.append("| # | Location | Risk | Incidents | Months Active | Trend 90d | Confidence |")
    lines.append("|---|---|---:|---:|---:|---|---|")
    for i, r in top10.iterrows():
        lines.append(
            f"| {i+1} | {r['location_display']} | {r['persistent_risk_score']:.3f} | "
            f"{int(r['total_incidents'])} | {int(r['active_months_count'])} | "
            f"{r['trend_90d']} | {r['confidence_band']} |"
        )
    lines.append("")
    lines.append("## Where + When — Deployment Windows (Top 10)")
    lines.append("")
    lines.append("| # | Location | Top Day(s) | Top Time Window | Day-of-Month | Weekend Share | Confidence |")
    lines.append("|---|---|---|---|---|---:|---|")
    for i, r in top10.iterrows():
        dow = r["top_dow_1"] or "—"
        if r["top_dow_2"]:
            dow = f"{dow} + {r['top_dow_2']}"
        lines.append(
            f"| {i+1} | {r['location_display']} | {dow} | "
            f"{r['top_time_window_1'] or '—'} | {r['top_day_of_month_band']} | "
            f"{r['weekend_share']*100:.0f}% | {r['confidence_band']} |"
        )
    lines.append("")
    lines.append("## Operational Recommendations")
    lines.append("")
    lines.append("1. **Deploy against top-DOW / top-time window first.** "
                 "Focus directed patrol on each hotspot's highest-concentration window before "
                 "spreading resources to secondary windows.")
    lines.append("2. **Re-validate 'up-trend' hotspots in the next cycle.** "
                 "Locations flagged `trend_90d = up` with medium+ confidence warrant supervisor "
                 "ground-truth check and potential CPTED or landlord/business contact.")
    lines.append("3. **Treat low-confidence rows as appendix only.** "
                 "Do not brief `confidence_band = low` locations as hotspots; they are listed for "
                 "analyst awareness, not deployment targets.")
    lines.append("")
    lines.append("## Caveats (Plain Language)")
    lines.append("")
    lines.append("- Scoring mixes calls (CAD) and reports (RMS). Some records describe the same incident; "
                 "the score weights each source for its signal, not for a one-to-one event count.")
    lines.append("- Domestic-violence records are excluded via the T4 two-layer filter. Roster lag means "
                 "very recent DV cases may still be present.")
    lines.append("- Suspicious-person / suspicious-vehicle calls are included at low severity. High volume "
                 "at those call types can reflect vigilant callers as much as actual risk.")
    lines.append("- Address normalization buckets to 100-block segments; minor differences in how addresses "
                 "were entered can split a real hotspot across two rows. Use map context for ground truth.")
    lines.append("- This is not predictive policing. It describes historical concentration and recency, "
                 "not individuals or future certainty.")
    lines.append("")
    lines.append(f"_Generated from {stats['cad_final_kept']:,} CAD events + {stats['rms_final_kept']:,} RMS events "
                 f"across {stats['n_locations']:,} distinct locations._")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Command staff MD written: {path}")


def write_method_caveats(locs: pd.DataFrame, path: Path, stats: dict) -> None:
    """One-page method + caveats note (MVP+ scope, 2026-04-17 deadline change)."""
    lines = []
    lines.append("# T4 Persistent Hotspots — Method & Caveats (One-Page)")
    lines.append("")
    lines.append(f"**Horizon:** {HORIZON_START.date()} → {HORIZON_END.date()}  |  "
                 f"**Analysis date:** {ANALYSIS_DATE.date()}  |  "
                 f"**Locations scored (citywide):** {stats['n_locations']:,}  |  "
                 f"**Top 10 delivered.**")
    lines.append("")
    lines.append("## Inputs (read-only)")
    lines.append("")
    lines.append("- CAD: `Data/cad/yearly/2024*.xlsx`, `2025*.xlsx`, `Data/cad/monthly/2026_01..03_CAD.xlsx`")
    lines.append("- RMS: `Data/rms/yearly/2024*.xlsx`, `2025*.xlsx`, `Data/rms/monthly/2026_01..03_RMS.xlsx`")
    lines.append(f"- DV blocklist: `Data/dv_case_numbers_for_t4.csv` "
                 f"(1,536 cases; source_date_end max = {stats['dv_source_date_end']})")
    lines.append("")
    lines.append("## Filtering")
    lines.append("")
    lines.append("- **CAD:** keep rows whose `Incident` matches a group/fight severity rule "
                 "(shots fired 5, aggravated assault 4, fight/group/simple assault 3, "
                 "disturbance/suspicious 2); exclude `HowReported=Self-Initiated` and "
                 "dispositions `Unfounded|Canceled|Checked OK`.")
    lines.append("- **RMS:** keep NIBRS Part 1 / violent (`09A/B=10, 120=7, 13A=5, 13B=3, "
                 "13C=2, 220=3, 240=2`); apply T4 two-layer DV exclusion (Layer 1 "
                 "case-number blocklist anti-join; Layer 2 type fallback) **before** scoring.")
    lines.append("- **Address normalization:** strip city/state/zip, strip unit/apt, standardize "
                 "suffixes, bucket house numbers to `NNN Block Street`, alphabetize intersections.")
    lines.append("")
    lines.append("## Scoring")
    lines.append("")
    lines.append("Four components per location, each min-max normalized to [0,1]:")
    lines.append("")
    lines.append("1. **frequency** — kept event count")
    lines.append("2. **persistence** — distinct year-months with ≥1 event")
    lines.append("3. **recency-weighted** — Σ decay(event_date, analysis_date)")
    lines.append("4. **severity-weighted** — Σ (severity × decay)")
    lines.append("")
    lines.append("Recency decay: ≤28d=1.00, ≤90d=0.75, ≤180d=0.50, 181+d=0.25.")
    lines.append("")
    lines.append("```")
    lines.append("persistent_risk_score = 0.20*freq + 0.30*persistence + 0.20*recency + 0.30*severity")
    lines.append("```")
    lines.append("")
    lines.append("Weights tilt toward persistence + severity over raw call volume.")
    lines.append("")
    lines.append("## Qualitative Confidence Flag")
    lines.append("")
    lines.append("- **high** — ≥20 incidents AND ≥6 active months AND ≥10 active weeks")
    lines.append("- **medium** — ≥8 incidents AND ≥3 active months")
    lines.append("- **low** — everything else (appendix only, do not brief)")
    lines.append("")
    lines.append("## Temporal Bins")
    lines.append("")
    lines.append("- Time-of-day: Early Morning 00–03, Morning 04–07, Morning Peak 08–11, "
                 "Afternoon 12–15, Evening Peak 16–19, Night 20–23.")
    lines.append("- Day-of-month bands: early (1–10), mid (11–20), late (21–31).")
    lines.append("- Weekend = Sat+Sun; Weekday = Mon–Fri.")
    lines.append("- `trend_90d`: last 90d vs prior 90d; `up` if ratio ≥1.20, `down` if ≤0.80, else `flat`.")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append(f"- **Event counts:** CAD {stats['cad_final_kept']:,} + RMS {stats['rms_final_kept']:,} "
                 f"kept after filters. CAD calls and RMS reports may describe the same incident; "
                 f"scoring weights each source for signal, not as a 1-to-1 event pair.")
    lines.append(f"- **DV exclusion:** {stats['excluded_dv_case_match']:,} RMS rows excluded by "
                 f"case-number blocklist; {stats['excluded_type_fallback']:,} by type fallback. "
                 f"Roster lag means very recent DV may still slip through.")
    lines.append("- **Spatial enrichment deferred:** lat/long, Post, PDZone, Grid are not joined to "
                 "output. Use ArcGIS Pro spatial join against raw CAD for overlays.")
    lines.append("- **Address-splitting risk:** minor typing differences can split one real hotspot "
                 "across two rows (e.g., `100 Block Main St` vs `100 Main St`). Use map context.")
    lines.append("- **Suspicious calls at low severity (2):** high volume there reflects vigilant "
                 "callers as much as actual risk; score weighting prevents dominance.")
    lines.append("- **CAD-side DV:** master-prompt DV filter runs on RMS only; CAD domestic calls "
                 "are out of scope for this product.")
    lines.append("- **Known source anomaly:** `2026_02_RMS.xlsx` was a 0-byte stub until re-exported "
                 "2026-04-16 (see `Docs/data_gaps.md`); any older run would have missed ~539 KB.")
    lines.append("- **Not predictive policing.** Historical risk patterning only. Field supervisors "
                 "ground-truth before deployment decisions.")
    lines.append("")
    lines.append(f"## Reproducibility")
    lines.append("")
    lines.append("```")
    lines.append("python -m Scripts.t4.persistent_hotspots")
    lines.append("```")
    lines.append("")
    lines.append(f"Full citywide CSV (all {stats['n_locations']:,} locations) is cached at "
                 f"`_overnight/persistent_hotspots/T4_persistent_hotspots_full_citywide.csv` "
                 f"for analyst drill-down.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Method & caveats note written: {path}")


def _unused_write_technical_appendix_deep(locs: pd.DataFrame, path: Path, stats: dict) -> None:
    lines = []
    lines.append("# T4 Persistent Hotspots — Technical Appendix")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("Strategic persistent-hotspot patrol product for group/fight-relevant incidents. "
                 "Supports patrol allocation decisions by describing historical concentration, persistence, "
                 "recency, and severity at the location level. Not a predictive model.")
    lines.append("")
    lines.append("## Data Sources & Horizon")
    lines.append("")
    lines.append(f"- **Horizon:** `{HORIZON_START.date()}` through `{HORIZON_END.date()}`")
    lines.append(f"- **Analysis date (recency anchor):** `{ANALYSIS_DATE.date()}`")
    lines.append("- **CAD:** `Data/cad/yearly/2024_CAD_ALL.xlsx`, `Data/cad/yearly/2025_CAD_ALL.xlsx`, "
                 "`Data/cad/monthly/2026_01_CAD.xlsx` .. `2026_03_CAD.xlsx`")
    lines.append("- **RMS:** `Data/rms/yearly/2024_ALL_RMS.xlsx`, `Data/rms/yearly/2025_ALL_RMS.xlsx`, "
                 "`Data/rms/monthly/2026_01_RMS.xlsx` .. `2026_03_RMS.xlsx`")
    lines.append("- **DV blocklist:** `Data/dv_case_numbers_for_t4.csv` "
                 f"(1,536 case numbers; source_date_end max = {stats['dv_source_date_end']})")
    lines.append("")
    lines.append("## Inclusion / Exclusion Logic")
    lines.append("")
    lines.append("### CAD")
    lines.append("- Keep rows whose `Incident` matches a group/fight severity rule (see table below).")
    lines.append("- Exclude `HowReported = Self-Initiated` (per master prompt §6.3 — patrol-presence, not demand).")
    lines.append(f"- Exclude dispositions: {sorted(EXCLUDED_DISPOSITIONS)}.")
    lines.append("- Deduplicate on `ReportNumberNew`.")
    lines.append("")
    lines.append("### RMS")
    lines.append("- Keep rows with a Part 1 / violent NIBRS prefix (see table below).")
    lines.append("- Apply two-layer DV exclusion BEFORE scoring:")
    lines.append("  - Layer 1: anti-join against `Data/dv_case_numbers_for_t4.csv` (case-number match).")
    lines.append("  - Layer 2: type fallback via `build_dv_type_set()` + `flag_dv_by_type()`.")
    lines.append("- Deduplicate on `CaseNumber`.")
    lines.append("")
    lines.append("### Address Normalization")
    lines.append("- Strip leading `,` or `&` and trailing `, Hackensack, NJ, 07601`.")
    lines.append("- Remove unit/apt/suite tokens.")
    lines.append("- Standardize suffixes (Street→St, Avenue→Ave, Place→Pl, Boulevard→Blvd, Road→Rd, etc.).")
    lines.append("- Bucket street-segment addresses to `NNN Block Street Name` (100-block hundreds).")
    lines.append("- Alphabetize intersection components; emit as `A St & B St`.")
    lines.append("- Drop rows whose address cannot resolve to a location key.")
    lines.append("")
    lines.append("## CAD Severity Rules (ordered, first match wins)")
    lines.append("")
    lines.append("| Pattern (substring, case-insensitive) | Severity |")
    lines.append("|---|---:|")
    for pat, pts in CAD_SEVERITY_RULES:
        lines.append(f"| `{pat}` | {pts} |")
    lines.append("")
    lines.append("## RMS Severity (NIBRS Prefix)")
    lines.append("")
    lines.append("| NIBRS | Severity |")
    lines.append("|---|---:|")
    for k, v in RMS_SEVERITY_BY_NIBRS.items():
        lines.append(f"| `{k}` | {v} |")
    lines.append("")
    lines.append("## Score Formula")
    lines.append("")
    lines.append("For each location key, compute four components over the horizon:")
    lines.append("")
    lines.append("- **frequency** = count of kept CAD+RMS events")
    lines.append("- **persistence** = count of distinct year-months with ≥1 kept event")
    lines.append("- **recency-weighted** = Σ decay(event_date, analysis_date)")
    lines.append("- **severity-weighted** = Σ severity × decay")
    lines.append("")
    lines.append("Recency decay (master prompt §7.3):")
    lines.append("")
    lines.append("| Age from analysis_date | Multiplier |")
    lines.append("|---|---:|")
    lines.append("| ≤ 28 days | 1.00 |")
    lines.append("| 29–90 days | 0.75 |")
    lines.append("| 91–180 days | 0.50 |")
    lines.append("| 181+ days | 0.25 |")
    lines.append("")
    lines.append("Each component is min-max normalized across all scored locations to `[0,1]`, then combined:")
    lines.append("")
    lines.append("```")
    lines.append("persistent_risk_score =")
    lines.append("    0.20 * freq_n + 0.30 * persistence_n + 0.20 * recency_n + 0.30 * severity_n")
    lines.append("```")
    lines.append("")
    lines.append("Weights tilt toward **persistence + severity** over raw frequency so that a location "
                 "with moderate volume but sustained month-over-month activity and serious event types "
                 "outranks a short burst of low-severity calls.")
    lines.append("")
    lines.append("## Trend 90d")
    lines.append("")
    lines.append("Compare last 90 days (`analysis_date - 90d → analysis_date`) to prior 90 days.")
    lines.append("- `up` if last/prior ≥ 1.20 (or prior=0 and last>0)")
    lines.append("- `down` if last/prior ≤ 0.80")
    lines.append("- `flat` otherwise")
    lines.append("")
    lines.append("## Confidence Band")
    lines.append("")
    lines.append("| Band | Requires |")
    lines.append("|---|---|")
    lines.append("| high   | ≥ 20 incidents AND ≥ 6 active months AND ≥ 10 active weeks |")
    lines.append("| medium | ≥ 8 incidents AND ≥ 3 active months |")
    lines.append("| low    | everything else — appendix only, do not brief as hotspot |")
    lines.append("")
    lines.append("## Temporal Bin Definitions")
    lines.append("")
    lines.append("### Time-of-Day (CAD time_of_call / RMS incident_date)")
    lines.append("")
    lines.append("| Label | Hours |")
    lines.append("|---|---|")
    for label, lo, hi in TOD_BINS:
        lines.append(f"| {label} | {lo:02d}:00–{hi-1:02d}:59 |")
    lines.append("")
    lines.append("### Day-of-Month Bands")
    lines.append("")
    lines.append("| Band | Days |")
    lines.append("|---|---|")
    lines.append("| early  | 1–10 |")
    lines.append("| mid    | 11–20 |")
    lines.append("| late   | 21–31 |")
    lines.append("")
    lines.append("### Weekend / Weekday")
    lines.append("")
    lines.append("- Weekend = Saturday + Sunday.")
    lines.append("- Weekday = Monday–Friday.")
    lines.append("")
    lines.append("## Validation Checks Performed")
    lines.append("")
    lines.append(f"- CAD rows in horizon: **{stats['cad_total_in_horizon']:,}**")
    lines.append(f"- CAD rows after group/fight severity filter: **{stats['cad_group_fight_relevant']:,}**")
    lines.append(f"- CAD rows after self-initiated exclusion: **{stats['cad_after_self_init_excl']:,}**")
    lines.append(f"- CAD rows after disposition exclusion (final kept): **{stats['cad_final_kept']:,}**")
    lines.append(f"- RMS rows in horizon: **{stats['rms_total_in_horizon']:,}**")
    lines.append(f"- RMS rows excluded by DV case-number blocklist: **{stats['excluded_dv_case_match']:,}**")
    lines.append(f"- RMS rows excluded by DV type fallback: **{stats['excluded_type_fallback']:,}**")
    lines.append(f"- RMS rows after Part-1 severity filter (final kept): **{stats['rms_final_kept']:,}**")
    lines.append(f"- Distinct location keys scored: **{stats['n_locations']:,}**")
    lines.append(f"- Schema check: all {len(OUTPUT_COLUMNS)} required CSV columns present → **PASS**")
    lines.append("")
    lines.append("## Caveats & Deferred Spatial Enrichment")
    lines.append("")
    lines.append("- `latitude` / `longitude` not yet joined to output rows — spatial enrichment deferred "
                 "pending address geocoding step (see ESRI backfill CLAUDE.md for geocoding approach).")
    lines.append("- Post / PDZone / Grid not joined to output; use ArcGIS Pro spatial join against CAD raw "
                 "data for that overlay.")
    lines.append("- DV roster `source_date_end` max is the most recent run of the DV ETL — very recent DV "
                 "incidents may remain in RMS if the roster has not been regenerated. Type fallback is the "
                 "safety net but will not catch every case.")
    lines.append("- Sexual-assault severity is flagged in CAD for statistical weighting only; CAD-level DV "
                 "filtering is out of scope for this product (master prompt §6.7 blind spot).")
    lines.append("- RMS February 2026 file was re-exported 2026-04-16 after an earlier 0-byte stub "
                 "(see `Docs/data_gaps.md`). A previous run would have missed ~539 KB of data.")
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append("```")
    lines.append("python -m Scripts.t4.persistent_hotspots")
    lines.append("```")
    lines.append("")
    lines.append(f"Exact horizon: `{HORIZON_START.date()} → {HORIZON_END.date()}` (analysis anchor `{ANALYSIS_DATE.date()}`).")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Technical appendix MD written: {path}")


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    # Validate required input paths
    for name, p in PATHS.items():
        if name in ("deliverables", "overnight"):
            continue
        if not p.exists():
            log.error(f"Required path missing: {name} -> {p}")
            sys.exit(1)

    PATHS["overnight"].mkdir(parents=True, exist_ok=True)
    PATHS["deliverables"].mkdir(parents=True, exist_ok=True)

    # 1. Load
    cad_raw = load_cad_window()
    rms_raw = load_rms_window()

    # 2. DV exclusion
    dv_blocklist, dv_src_end = load_dv_blocklist()
    dv_type_set = build_dv_type_set(PATHS["incident_type_map"], PATHS["calltype_categories"])
    rms_dv_clean, dv_stats = apply_dv_exclusion(rms_raw, dv_blocklist, dv_type_set)

    # 3. Filter CAD to group/fight-relevant + citizen
    cad_kept, cad_stats = prep_cad_incidents(cad_raw)

    # 4. Filter RMS to Part 1 severity
    rms_kept = prep_rms_incidents(rms_dv_clean)
    log.info(f"RMS Part-1 kept (post-DV): {len(rms_kept):,}")

    # 5. Unify & feature-engineer
    events = build_unified(cad_kept, rms_kept)
    events_path = PATHS["overnight"] / "unified_events.csv"
    events.drop(columns=["raw_address"]).to_csv(events_path, index=False)
    log.info(f"Unified events written: {events_path} ({len(events):,} rows)")

    # 6. Aggregate to locations
    locs = aggregate_locations(events)

    # 7. Composite score + confidence + recommendations
    locs = compute_composite(locs)

    # 8. Sanity checks
    assert len(locs) > 0, "No locations scored"
    top = locs.head(20)
    if (top["top_time_window_1"] == "").any():
        log.warning("Some top-20 locations missing top_time_window_1")
    if (top["deployment_window_recommendation"] == "").any():
        raise RuntimeError("Sanity check failed: empty deployment_window_recommendation in top 20")

    # 9. Stats bundle
    stats = {
        "cad_total_in_horizon":        cad_stats["cad_total_in_horizon"],
        "cad_group_fight_relevant":    cad_stats["cad_group_fight_relevant"],
        "cad_after_self_init_excl":    cad_stats["cad_after_self_init_excl"],
        "cad_final_kept":              cad_stats["cad_after_disposition_excl"],
        "rms_total_in_horizon":        dv_stats["total_rms_before_filter"],
        "excluded_dv_case_match":      dv_stats["excluded_dv_case_match"],
        "excluded_type_fallback":      dv_stats["excluded_type_fallback"],
        "rms_scoring_ready":           dv_stats["scoring_ready_rows"],
        "rms_final_kept":              int(len(rms_kept)),
        "n_locations":                 int(len(locs)),
        "dv_source_date_end":          dv_src_end,
    }
    (PATHS["overnight"] / "run_stats.json").write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")

    # 10. Write deliverables
    csv_path = PATHS["deliverables"] / "T4_persistent_hotspots_citywide.csv"
    cmd_path = PATHS["deliverables"] / "T4_persistent_hotspots_command_staff.md"
    tech_path = PATHS["deliverables"] / "T4_persistent_hotspots_technical_appendix.md"

    # MVP+ scope per 2026-04-17 deadline change: ship top-10 CSV, command
    # one-pager, and one-page method/caveats note. Full citywide CSV is still
    # written to _overnight/ for analyst reference.
    (PATHS["overnight"] / "T4_persistent_hotspots_full_citywide.csv").parent.mkdir(parents=True, exist_ok=True)
    locs.to_csv(PATHS["overnight"] / "T4_persistent_hotspots_full_citywide.csv",
                columns=OUTPUT_COLUMNS, index=False)
    write_csv(locs, csv_path, top_n=10)
    write_command_staff_md(locs, cmd_path, stats)
    write_method_caveats(locs, tech_path, stats)

    # 11. Print summary
    print()
    print("=" * 60)
    print("T4 Persistent Hotspots — Run Complete")
    print("=" * 60)
    print(f"Horizon:        {HORIZON_START.date()} → {HORIZON_END.date()}")
    print(f"CAD final kept: {stats['cad_final_kept']:,}")
    print(f"RMS final kept: {stats['rms_final_kept']:,}")
    print(f"Locations:      {stats['n_locations']:,}")
    print()
    print("Top 5:")
    for _, r in locs.head(5).iterrows():
        print(f"  {r['persistent_risk_score']:.3f}  {r['location_display']:<48}  "
              f"n={int(r['total_incidents']):>3}  months={int(r['active_months_count']):>2}  "
              f"{r['confidence_band']:<6}  {r['deployment_window_recommendation']}")
    print()
    print(f"CSV:            {csv_path}")
    print(f"Command staff:  {cmd_path}")
    print(f"Tech appendix:  {tech_path}")


if __name__ == "__main__":
    main()
