"""
T4 DV Type Fallback — Layer 2 of the two-layer DV exclusion filter.

Matches RMS IncidentType1/2/3 values against known DV/domestic patterns
from incident_type_map.csv and CallType_Categories.csv.

Runs AFTER the Layer 1 case-number blocklist anti-join so it only needs
to catch rows the blocklist missed (roster lag, uncoded cases).

Usage:
    from Scripts.t4.type_fallback import build_dv_type_set, flag_dv_by_type
"""
import re
from pathlib import Path
from typing import Set

import pandas as pd


# ── Hardcoded DV patterns (always match, case-insensitive) ───────────
# These catch the statutory citation variants in Hackensack RMS/CAD data.
DV_PATTERNS = [
    r'domestic\s*violence',
    r'domestic\s*dispute',
    r'2c[:\s]*25[\-\s]*21',      # NJ 2C:25-21 (Prevention of Domestic Violence Act)
    r'restraining\s*order',
    r'\btro\b',                    # Temporary Restraining Order
    r'\bfro\b',                    # Final Restraining Order
    r'service\s*-?\s*tro',
]

_DV_RE = re.compile('|'.join(DV_PATTERNS), re.IGNORECASE)


def build_dv_type_set(
    incident_type_map_path: str | Path | None = None,
    calltype_categories_path: str | Path | None = None,
) -> Set[str]:
    """
    Build a set of lowercase DV-adjacent incident type strings from reference
    files. These supplement the regex patterns above for exact-match fallback.

    Returns lowercased strings that should trigger DV exclusion.
    """
    dv_types: Set[str] = set()

    # incident_type_map.csv — 'raw' column; all rows are DV-adjacent by definition
    if incident_type_map_path and Path(incident_type_map_path).exists():
        itm = pd.read_csv(incident_type_map_path, encoding='utf-8-sig')
        for col in ['raw', 'canonical']:
            if col in itm.columns:
                vals = itm[col].dropna().str.strip().str.lower()
                dv_types.update(vals)

    # CallType_Categories.csv — filter to rows containing 'domestic' in Incident
    if calltype_categories_path and Path(calltype_categories_path).exists():
        ctc = pd.read_csv(calltype_categories_path, encoding='utf-8-sig')
        if 'Incident' in ctc.columns:
            mask = ctc['Incident'].str.lower().str.contains('domestic', na=False)
            dv_types.update(ctc.loc[mask, 'Incident'].str.strip().str.lower())
        if 'Incident_Norm' in ctc.columns:
            mask = ctc['Incident_Norm'].str.lower().str.contains('domestic', na=False)
            dv_types.update(ctc.loc[mask, 'Incident_Norm'].str.strip().str.lower())

    return dv_types


def is_dv_type(value: str, dv_type_set: Set[str] | None = None) -> bool:
    """Check if a single incident type string is DV-adjacent."""
    if pd.isna(value) or not str(value).strip():
        return False
    lower = str(value).strip().lower()
    if _DV_RE.search(lower):
        return True
    if dv_type_set and lower in dv_type_set:
        return True
    return False


def flag_dv_by_type(
    df: pd.DataFrame,
    dv_type_set: Set[str] | None = None,
    type_columns: list[str] | None = None,
) -> pd.Series:
    """
    Return a boolean Series: True where ANY of the incident type columns
    matches a DV pattern or is in the DV type set.

    Args:
        df: RMS DataFrame with snake_case columns
        dv_type_set: from build_dv_type_set(); if None, uses regex only
        type_columns: defaults to ['incident_type_1', 'incident_type_2', 'incident_type_3']

    Returns:
        pd.Series[bool] aligned to df.index
    """
    if type_columns is None:
        type_columns = ['incident_type_1', 'incident_type_2', 'incident_type_3']

    present_cols = [c for c in type_columns if c in df.columns]
    if not present_cols:
        return pd.Series(False, index=df.index)

    result = pd.Series(False, index=df.index)
    for col in present_cols:
        result |= df[col].apply(lambda v: is_dv_type(v, dv_type_set))

    return result


# ── Standalone test ──────────────────────────────────────────────────
if __name__ == '__main__':
    from pathlib import Path

    ONEDRIVE = Path(r'C:\Users\carucci_r\OneDrive - City of Hackensack')
    ITM = ONEDRIVE / '02_ETL_Scripts' / 'dv_doj' / 'docs' / 'mappings' / 'incident_type_map.csv'
    CTC = ONEDRIVE / '09_Reference' / 'Classifications' / 'CallTypes' / 'CallType_Categories.csv'

    dv_set = build_dv_type_set(ITM, CTC)
    print(f'DV type set ({len(dv_set)} entries):')
    for t in sorted(dv_set):
        print(f'  {t}')

    print(f'\nRegex patterns: {len(DV_PATTERNS)}')

    test_values = [
        'Domestic Violence - 2C:25-21',
        'Simple Assault - 2C:12-1a',
        'Domestic Dispute',
        'domestic dispute',
        'Aggravated Assault - 2C:12-1b',
        'Service - TRO',
        'Shoplifting - 2C:20-11',
        'Fraud',
        None,
        '',
    ]
    print('\nTest matches:')
    for v in test_values:
        result = is_dv_type(v, dv_set)
        print(f'  {str(v):45s} -> {"DV" if result else "---"}')
