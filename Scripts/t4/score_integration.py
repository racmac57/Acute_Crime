"""
T4 Score Integration — DV exclusion + Tier 1/Tier 2 scoring pipeline.

Applies the two-layer DV exclusion filter (blocklist + type fallback)
before computing Tier 1 CAD and Tier 2 RMS Part 1 scores with recency
decay and repeat-location boost per Master Prompt v3 §7.

Usage:
    python -m Scripts.t4.score_integration --help
    python -m Scripts.t4.score_integration \\
        --cycle-id T4_C01W02 \\
        --cad-pull-start 2026-03-01 --cad-pull-end 2026-03-28 \\
        --rms-pull-start 2026-03-01 --rms-pull-end 2026-04-11 \\
        --analysis-date 2026-03-28
"""
import argparse
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from Scripts.t4.column_norm import normalize_columns, standardize_case_number
from Scripts.t4.type_fallback import build_dv_type_set, flag_dv_by_type

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# ── Paths (from Docs/t4_config_and_aliases.md §2) ───────────────────
ONEDRIVE = Path(r'C:\Users\carucci_r\OneDrive - City of Hackensack')
PROJECT  = ONEDRIVE / '10_Projects' / 'Acute_Crime'

PATHS = {
    'dv_blocklist':       PROJECT / 'Data' / 'dv_case_numbers_for_t4.csv',
    'incident_type_map':  ONEDRIVE / '02_ETL_Scripts' / 'dv_doj' / 'docs' / 'mappings' / 'incident_type_map.csv',
    'calltype_categories': ONEDRIVE / '09_Reference' / 'Classifications' / 'CallTypes' / 'CallType_Categories.csv',
    'rms_monthly':        PROJECT / 'Data' / 'rms' / 'monthly',
    'rms_yearly':         PROJECT / 'Data' / 'rms' / 'yearly',
    'cad_monthly':        PROJECT / 'Data' / 'cad' / 'monthly',
    'cad_yearly':         PROJECT / 'Data' / 'cad' / 'yearly',
    'output_dir':         PROJECT / 'Output',
}

# ── Tier 1 CAD scoring (Master Prompt §7.1) ─────────────────────────
# Keys are lowercased substrings to match against the 'incident' column.
TIER1_SCORES = {
    'shots fired':       5,
    'weapon':            5,
    'aggravated assault': 4,
    'fight':             3,
    'group fight':       3,
    'disorderly group':  3,
    'group':             3,
    'suspicious person': 2,
    'suspicious vehicle': 2,
    'suspicious':        2,
    'ordinance':         1,
    'city ordinance':    1,
}

def extract_nibrs_code_key(nibrs_raw: str) -> str:
    """
    RMS exports often store NIBRS as '13A = Aggravated Assault' or '120 = Robbery'.
    Tier 2 lookup keys are the leading code token only.
    """
    if pd.isna(nibrs_raw):
        return ''
    s = str(nibrs_raw).strip().upper()
    m = re.match(r'^(\d{2}[A-Z]|\d{3})\b', s)
    return m.group(1) if m else ''


# ── Tier 2 RMS Part 1 bonus (Master Prompt §7.2) ────────────────────
# Keyed by NIBRS code prefix. Applied on top of Tier 1.
TIER2_SCORES = {
    '09A': 10, '09B': 10,                      # Homicide
    '120': 7,                                    # Robbery (default; firearm = 7)
    '13A': 5,                                    # Aggravated Assault (confirmed RMS)
    '220': 3,                                    # Burglary
    '240': 2,                                    # Motor Vehicle Theft
    '23A': 1, '23B': 1, '23C': 1, '23D': 1,    # Larceny subtypes (threshold: >= $500)
    '23E': 1, '23F': 1, '23G': 1, '23H': 1,
}


# ── Recency decay (Master Prompt §7.3) ──────────────────────────────
def recency_multiplier(event_date: datetime, analysis_date: datetime) -> float:
    days = (analysis_date - event_date).days
    if days <= 28:
        return 1.00
    if days <= 90:
        return 0.75
    if days <= 180:
        return 0.50
    return 0.25


# ── Data loading ─────────────────────────────────────────────────────
def load_rms(start: str, end: str) -> pd.DataFrame:
    """Load RMS XLSX files covering the date range, normalize columns."""
    frames = []
    for folder in [PATHS['rms_yearly'], PATHS['rms_monthly']]:
        if not folder.exists():
            continue
        for f in sorted(folder.glob('*.xlsx')):
            if f.stat().st_size == 0:
                log.warning(f'Skipping 0-byte file: {f.name}')
                continue
            df = pd.read_excel(f, dtype=str)
            df = normalize_columns(df)
            frames.append(df)

    if not frames:
        log.error('No RMS files found')
        sys.exit(1)

    rms = pd.concat(frames, ignore_index=True).drop_duplicates(subset='case_number')

    # Parse dates, filter to window
    for col in ['incident_date', 'report_date']:
        if col in rms.columns:
            rms[f'{col}_parsed'] = pd.to_datetime(rms[col], errors='coerce')

    date_col = 'incident_date_parsed' if 'incident_date_parsed' in rms.columns else 'report_date_parsed'
    rms = rms[rms[date_col].notna()]
    rms = rms[(rms[date_col] >= start) & (rms[date_col] <= end)]

    log.info(f'RMS loaded: {len(rms):,} rows in window {start} to {end}')
    return rms


def load_cad(start: str, end: str) -> pd.DataFrame:
    """Load CAD XLSX files covering the date range, normalize columns."""
    frames = []
    for folder in [PATHS['cad_yearly'], PATHS['cad_monthly']]:
        if not folder.exists():
            continue
        for f in sorted(folder.glob('*.xlsx')):
            if f.stat().st_size == 0:
                log.warning(f'Skipping 0-byte file: {f.name}')
                continue
            df = pd.read_excel(f, dtype=str)
            df = normalize_columns(df)
            frames.append(df)

    if not frames:
        log.error('No CAD files found')
        sys.exit(1)

    cad = pd.concat(frames, ignore_index=True).drop_duplicates(subset='report_number_new')

    # Parse dates
    for col in ['time_of_call']:
        if col in cad.columns:
            cad[f'{col}_parsed'] = pd.to_datetime(cad[col], errors='coerce')

    date_col = 'time_of_call_parsed'
    if date_col in cad.columns:
        cad = cad[cad[date_col].notna()]
        cad = cad[(cad[date_col] >= start) & (cad[date_col] <= end)]

    log.info(f'CAD loaded: {len(cad):,} rows in window {start} to {end}')
    return cad


def load_dv_blocklist() -> set:
    """Load PII-safe DV case number blocklist."""
    p = PATHS['dv_blocklist']
    if not p.exists():
        log.error(f'DV blocklist not found: {p}')
        sys.exit(1)

    bl = pd.read_csv(p)
    cases = set(bl['case_number'].dropna().str.strip().str.upper())
    log.info(f'DV blocklist loaded: {len(cases):,} case numbers '
             f'(source_date_end max: {bl["source_date_end"].max()})')
    return cases


# ── DV exclusion (two-layer filter) ─────────────────────────────────
def apply_dv_exclusion(
    rms: pd.DataFrame,
    dv_blocklist: set,
    dv_type_set: set,
    rms_pull_start: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Apply two-layer DV exclusion. Returns:
        (scoring_ready_df, excluded_df, exclusion_stats)
    """
    total_before = len(rms)

    # Standardize case numbers for matching
    rms['_cn_std'] = rms['case_number'].apply(standardize_case_number)

    # Layer 1: case-number blocklist anti-join
    layer1_mask = rms['_cn_std'].isin(dv_blocklist)

    # Layer 2: type fallback (on rows NOT caught by Layer 1)
    layer2_mask = flag_dv_by_type(rms, dv_type_set) & ~layer1_mask

    # Combined exclusion
    excluded_mask = layer1_mask | layer2_mask

    exclusion_stats = {
        'total_rms_before_filter': total_before,
        'excluded_dv_case_match': int(layer1_mask.sum()),
        'excluded_type_fallback': int(layer2_mask.sum()),
        'total_excluded': int(excluded_mask.sum()),
        'scoring_ready_rows': int((~excluded_mask).sum()),
    }

    excluded = rms[excluded_mask].copy()
    excluded['exclusion_reason'] = 'dv_case_match'
    excluded.loc[layer2_mask[excluded_mask], 'exclusion_reason'] = 'type_fallback'

    scoring_ready = rms[~excluded_mask].drop(columns=['_cn_std'])
    excluded = excluded.drop(columns=['_cn_std'])

    log.info(
        f'DV exclusion: {exclusion_stats["excluded_dv_case_match"]} by case match, '
        f'{exclusion_stats["excluded_type_fallback"]} by type fallback, '
        f'{exclusion_stats["scoring_ready_rows"]:,} rows scoring-ready'
    )

    return scoring_ready, excluded, exclusion_stats


# ── Tier 1 scoring ──────────────────────────────────────────────────
def score_tier1(incident: str) -> int:
    """Assign Tier 1 CAD points based on incident type substring match."""
    if pd.isna(incident):
        return 0
    lower = str(incident).strip().lower()
    for pattern, pts in TIER1_SCORES.items():
        if pattern in lower:
            return pts
    return 0


# ── Tier 2 scoring ──────────────────────────────────────────────────
def score_tier2(nibrs_code: str, total_value_stolen: str = None) -> int:
    """Assign Tier 2 RMS Part 1 bonus based on NIBRS code."""
    if pd.isna(nibrs_code):
        return 0
    code = extract_nibrs_code_key(nibrs_code)
    # Larceny threshold: >= $500
    if code.startswith('23'):
        try:
            val = float(total_value_stolen) if total_value_stolen and not pd.isna(total_value_stolen) else 0
        except (ValueError, TypeError):
            val = 0
        if val < 500:
            return 0
    return TIER2_SCORES.get(code, 0)


# ── Location scoring ────────────────────────────────────────────────
def compute_location_scores(
    cad: pd.DataFrame,
    rms: pd.DataFrame,
    analysis_date: datetime,
    cycle_start: datetime,
) -> pd.DataFrame:
    """
    Compute weighted location scores per Master Prompt §7.5:
    location_score = [Σ(tier1 × decay) + Σ(tier2 × decay)] × location_boost

    Returns a DataFrame with one row per canonical location.
    """
    # ── Tier 1: CAD citizen-generated scoring ────────────────────────
    # Filter to citizen-generated (exclude Self-Initiated; resolve Radio per §6.3)
    if 'how_reported' in cad.columns:
        citizen_mask = ~cad['how_reported'].str.lower().isin(['self-initiated'])
        # Radio entries without linked citizen call should be excluded,
        # but that linkage check requires ReportNumberNew cross-reference.
        # For now, include Radio — flag in Data Quality Note.
        cad_citizen = cad[citizen_mask].copy()
        cad_self_init = cad[~citizen_mask].copy()
    else:
        cad_citizen = cad.copy()
        cad_self_init = pd.DataFrame()

    cad_citizen['tier1_pts'] = cad_citizen['incident'].apply(score_tier1)
    cad_citizen['tier1_pts'] = cad_citizen['tier1_pts'].where(cad_citizen['tier1_pts'] > 0)
    cad_scored = cad_citizen[cad_citizen['tier1_pts'].notna()].copy()

    if 'time_of_call_parsed' in cad_scored.columns:
        cad_scored['decay'] = cad_scored['time_of_call_parsed'].map(
            lambda d: recency_multiplier(d, analysis_date) if pd.notna(d) else 0.0
        ).astype('float64')
    else:
        cad_scored['decay'] = 1.0

    cad_scored['tier1_weighted'] = cad_scored['tier1_pts'] * cad_scored['decay']

    # ── Tier 2: RMS Part 1 bonus ────────────────────────────────────
    rms['tier2_pts'] = rms.apply(
        lambda r: score_tier2(
            r.get('nibrs_classification', ''),
            r.get('total_value_stolen', None)
        ),
        axis=1,
    )
    rms_scored = rms[rms['tier2_pts'] > 0].copy()

    date_col = 'incident_date_parsed' if 'incident_date_parsed' in rms_scored.columns else None
    if date_col:
        rms_scored['decay'] = rms_scored[date_col].map(
            lambda d: recency_multiplier(d, analysis_date) if pd.notna(d) else 0.0
        ).astype('float64')
    else:
        rms_scored['decay'] = 1.0

    rms_scored['tier2_weighted'] = rms_scored['tier2_pts'] * rms_scored['decay']

    # ── Aggregate by location ────────────────────────────────────────
    # Use full_address_2 (CAD) and full_address (RMS) as proxy for Block_Final.
    # Full Block_Final normalization (§4) is a separate pipeline step.
    cad_loc_col = 'full_address_2' if 'full_address_2' in cad_scored.columns else 'full_address'
    rms_loc_col = 'full_address' if 'full_address' in rms_scored.columns else None

    cad_agg = (
        cad_scored.groupby(cad_loc_col)
        .agg(
            tier1_sum=('tier1_weighted', 'sum'),
            raw_count=('tier1_pts', 'count'),
            citizen_incidents_current_cycle=(
                'tier1_pts',
                lambda x: x[cad_scored.loc[x.index, 'decay'] == 1.0].count()
            ),
        )
        .rename_axis('location')
        .reset_index()
    )

    if rms_loc_col and not rms_scored.empty:
        rms_agg = (
            rms_scored.groupby(rms_loc_col)
            .agg(
                tier2_sum=('tier2_weighted', 'sum'),
                rms_part1_count=('tier2_pts', 'count'),
            )
            .rename_axis('location')
            .reset_index()
        )
        locations = cad_agg.merge(rms_agg, on='location', how='left')
    else:
        locations = cad_agg.copy()
        locations['tier2_sum'] = 0.0
        locations['rms_part1_count'] = 0

    locations['tier2_sum'] = locations['tier2_sum'].fillna(0)
    locations['rms_part1_count'] = locations['rms_part1_count'].fillna(0).astype(int)

    # ── Repeat-location boost (§7.4) ────────────────────────────────
    # >= 3 citizen-generated scoring incidents in current 28-day cycle = 1.25×
    locations['location_boost'] = locations['citizen_incidents_current_cycle'].apply(
        lambda n: 1.25 if n >= 3 else 1.0
    )

    # ── Final score (§7.5) ─────────────────────────────────────────��
    locations['weighted_score'] = (
        (locations['tier1_sum'] + locations['tier2_sum']) * locations['location_boost']
    )

    # Self-initiated counts
    if not cad_self_init.empty and cad_loc_col in cad_self_init.columns:
        si_counts = (
            cad_self_init.groupby(cad_loc_col)
            .size()
            .rename('self_init_count')
            .rename_axis('location')
            .reset_index()
        )
        locations = locations.merge(si_counts, on='location', how='left')
    locations['self_init_count'] = locations.get('self_init_count', pd.Series(0)).fillna(0).astype(int)

    locations = locations.sort_values('weighted_score', ascending=False).reset_index(drop=True)

    log.info(f'Scored {len(locations):,} locations; top score: {locations["weighted_score"].iloc[0]:.2f}')
    return locations


# ── Data Quality Note ────────────────────────────────────────────────
def generate_data_quality_note(
    exclusion_stats: dict,
    cad_count: int,
    rms_count: int,
    scored_locations: int,
    cycle_id: str,
    analysis_date: str,
    output_path: Path,
) -> None:
    """Write the Data Quality Note per Master Prompt §17 + DV extension."""
    note = {
        'cycle_id': cycle_id,
        'analysis_date': analysis_date,
        'generated': datetime.now().isoformat(),
        'cad_rows_in_window': cad_count,
        'rms_rows_in_window': rms_count,
        'dv_exclusion': exclusion_stats,
        'scored_locations': scored_locations,
        'notes': [
            'Radio entries included by default; manual review recommended per §6.3',
            'Block_Final normalization not yet implemented; using raw address as location key',
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(note, f, indent=2, default=str)

    log.info(f'Data Quality Note written to {output_path}')


# ── Main pipeline ────────────────────────────────────────────────────
def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the full scoring pipeline."""
    # Validate required parameters (Master Prompt §0)
    if not args.cycle_id:
        log.error('cycle_id is required. Outputs without cycle_id are invalid.')
        sys.exit(1)

    # Validate paths
    for name, path in PATHS.items():
        if name == 'output_dir':
            continue
        if not path.exists():
            log.error(f'Required path not found: {name} -> {path}')
            sys.exit(1)

    analysis_date = datetime.strptime(args.analysis_date, '%Y-%m-%d')
    cycle_start = datetime.strptime(args.cad_pull_start, '%Y-%m-%d')

    # Load data
    rms = load_rms(args.rms_pull_start, args.rms_pull_end)
    cad = load_cad(args.cad_pull_start, args.cad_pull_end)

    # Load DV exclusion inputs
    dv_blocklist = load_dv_blocklist()

    # Check DV roster covers analysis window
    bl_df = pd.read_csv(PATHS['dv_blocklist'])
    max_source_date = bl_df['source_date_end'].max()
    if max_source_date < args.rms_pull_start:
        log.error(
            f'[DV ROSTER LAG] Blocklist source_date_end ({max_source_date}) '
            f'< rms_pull_start ({args.rms_pull_start}). '
            f'Regenerate backfill_dv before proceeding.'
        )
        sys.exit(1)

    dv_type_set = build_dv_type_set(
        PATHS['incident_type_map'],
        PATHS['calltype_categories'],
    )

    # Apply DV exclusion BEFORE scoring (per plan order-of-operations)
    rms_scoring, rms_excluded, exclusion_stats = apply_dv_exclusion(
        rms, dv_blocklist, dv_type_set, args.rms_pull_start,
    )

    # Compute location scores
    locations = compute_location_scores(cad, rms_scoring, analysis_date, cycle_start)

    # Add cycle fields
    locations['cycle_id'] = args.cycle_id
    locations['cycle_7day'] = args.cycle_id
    locations['cycle_28day'] = args.cycle_id.rsplit('W', 1)[0] if 'W' in args.cycle_id else args.cycle_id

    # Assert cycle_id populated
    assert locations['cycle_id'].notna().all(), 'cycle_id must be non-null on all output rows'

    # Write outputs
    output_dir = PATHS['output_dir'] / args.cycle_id
    output_dir.mkdir(parents=True, exist_ok=True)

    locations_path = output_dir / f'{args.cycle_id}_scored_locations.csv'
    locations.to_csv(locations_path, index=False)
    log.info(f'Scored locations: {locations_path}')

    excluded_path = output_dir / f'{args.cycle_id}_dv_excluded.csv'
    rms_excluded.to_csv(excluded_path, index=False)
    log.info(f'DV excluded rows: {excluded_path}')

    dq_path = output_dir / f'{args.cycle_id}_data_quality_note.json'
    generate_data_quality_note(
        exclusion_stats, len(cad), len(rms),
        len(locations), args.cycle_id, args.analysis_date, dq_path,
    )

    print(f'\n{"="*60}')
    print(f'T4 Scoring Complete — {args.cycle_id}')
    print(f'{"="*60}')
    print(f'CAD rows:           {len(cad):,}')
    print(f'RMS rows (total):   {exclusion_stats["total_rms_before_filter"]:,}')
    print(f'DV excluded (case): {exclusion_stats["excluded_dv_case_match"]:,}')
    print(f'DV excluded (type): {exclusion_stats["excluded_type_fallback"]:,}')
    print(f'RMS scoring-ready:  {exclusion_stats["scoring_ready_rows"]:,}')
    print(f'Scored locations:   {len(locations):,}')
    print(f'Top score:          {locations["weighted_score"].iloc[0]:.2f}')
    print(f'Output dir:         {output_dir}')


def main():
    parser = argparse.ArgumentParser(description='T4 Hotspot Scoring Pipeline')
    parser.add_argument('--cycle-id', required=True, help='e.g. T4_C01W02')
    parser.add_argument('--cad-pull-start', required=True, help='YYYY-MM-DD')
    parser.add_argument('--cad-pull-end', required=True, help='YYYY-MM-DD')
    parser.add_argument('--rms-pull-start', required=True, help='YYYY-MM-DD')
    parser.add_argument('--rms-pull-end', required=True, help='YYYY-MM-DD (include 14-day buffer)')
    parser.add_argument('--analysis-date', required=True, help='YYYY-MM-DD (today for decay)')
    args = parser.parse_args()
    run_pipeline(args)


if __name__ == '__main__':
    main()
