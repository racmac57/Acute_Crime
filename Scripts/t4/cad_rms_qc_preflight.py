"""
T4 CAD/RMS QC Pre-flight — Optional upstream quality checks.

Validates CAD and RMS exports before they enter the scoring pipeline.
Aligns with Master Prompt §17 (Data Quality Checks) and
cad_rms_data_quality validators where available.

Usage:
    python -m Scripts.t4.cad_rms_qc_preflight \\
        --cad-pull-start 2026-03-01 --cad-pull-end 2026-03-28 \\
        --rms-pull-start 2026-03-01 --rms-pull-end 2026-04-11
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from Scripts.t4.column_norm import normalize_columns, standardize_case_number

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

ONEDRIVE = Path(r'C:\Users\carucci_r\OneDrive - City of Hackensack')
PROJECT  = ONEDRIVE / '10_Projects' / 'Acute_Crime'

# Hackensack bounding box (approximate, WGS84)
BBOX = {
    'lat_min': 40.860, 'lat_max': 40.920,
    'lon_min': -74.070, 'lon_max': -74.020,
}

# Valid HowReported values (from Standards how_reported_normalization_map.json)
VALID_HOW_REPORTED = {
    '9-1-1', 'canceled call', 'fax', 'mail', 'other - see notes',
    'phone', 'radio', 'self-initiated', 'teletype', 'virtual patrol',
    'walk-in', 'email',
}

# Disposition exclusions (Master Prompt §6.2)
DISPOSITION_EXCLUSIONS = {'unfounded', 'canceled', 'cancelled', 'checked ok'}


def load_files(folder_monthly: Path, folder_yearly: Path, start: str, end: str, dedup_col: str) -> pd.DataFrame:
    frames = []
    for folder in [folder_yearly, folder_monthly]:
        if not folder.exists():
            continue
        for f in sorted(folder.glob('*.xlsx')):
            if f.stat().st_size == 0:
                log.warning(f'SKIP 0-byte: {f.name}')
                continue
            df = pd.read_excel(f, dtype=str)
            df = normalize_columns(df)
            df['_source_file'] = f.name
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    if dedup_col in combined.columns:
        dupes = combined.duplicated(subset=dedup_col, keep='first')
        if dupes.any():
            log.warning(f'Dedup: {dupes.sum():,} duplicate {dedup_col} values removed')
        combined = combined[~dupes]

    return combined


def check_cad(cad: pd.DataFrame, start: str, end: str) -> list[dict]:
    """Run Master Prompt §17 checks on CAD data. Returns list of findings."""
    findings = []
    total = len(cad)
    if total == 0:
        findings.append({'check': 'CAD_EMPTY', 'severity': 'ERROR', 'detail': 'No CAD rows loaded'})
        return findings

    findings.append({'check': 'CAD_ROW_COUNT', 'severity': 'INFO', 'detail': f'{total:,} rows'})

    # Missing location (§17)
    if 'full_address_2' in cad.columns:
        null_addr = cad['full_address_2'].isna() | (cad['full_address_2'].str.strip() == '')
        pct = null_addr.sum() / total * 100
        sev = 'WARNING' if pct > 10 else 'INFO'
        findings.append({
            'check': 'CAD_MISSING_LOCATION',
            'severity': sev,
            'detail': f'{null_addr.sum():,} rows ({pct:.1f}%) missing address',
        })

    # Duplicate ReportNumberNew (§17)
    if 'report_number_new' in cad.columns:
        dupes = cad['report_number_new'].duplicated(keep=False)
        if dupes.any():
            findings.append({
                'check': 'CAD_DUPLICATE_REPORT_NUMBER',
                'severity': 'WARNING',
                'detail': f'{dupes.sum():,} rows with duplicate report_number_new',
            })

    # Invalid coordinates (§17)
    for coord_col, bound_key_min, bound_key_max in [
        ('latitude', 'lat_min', 'lat_max'),
        ('longitude', 'lon_min', 'lon_max'),
    ]:
        if coord_col in cad.columns:
            vals = pd.to_numeric(cad[coord_col], errors='coerce')
            null_coords = vals.isna().sum()
            out_of_bounds = ((vals < BBOX[bound_key_min]) | (vals > BBOX[bound_key_max])).sum()
            if null_coords > 0 or out_of_bounds > 0:
                findings.append({
                    'check': f'CAD_{coord_col.upper()}_QUALITY',
                    'severity': 'WARNING',
                    'detail': f'{null_coords} null, {out_of_bounds} outside Hackensack bbox',
                })

    # HowReported domain (§6.3)
    if 'how_reported' in cad.columns:
        raw_vals = cad['how_reported'].dropna().str.strip().str.lower().unique()
        unmapped = [v for v in raw_vals if v not in VALID_HOW_REPORTED]
        if unmapped:
            findings.append({
                'check': 'CAD_HOW_REPORTED_UNMAPPED',
                'severity': 'WARNING',
                'detail': f'{len(unmapped)} unmapped values: {unmapped[:10]}',
            })

        radio_count = (cad['how_reported'].str.lower() == 'radio').sum()
        si_count = (cad['how_reported'].str.lower() == 'self-initiated').sum()
        findings.append({
            'check': 'CAD_HOW_REPORTED_DISTRIBUTION',
            'severity': 'INFO',
            'detail': f'Radio={radio_count:,}, Self-Initiated={si_count:,} (review Radio per §6.3)',
        })

    # Disposition rates (§17)
    if 'disposition' in cad.columns:
        disp_lower = cad['disposition'].str.strip().str.lower()
        for disp in ['unfounded', 'canceled', 'checked ok', 'goa', 'g.o.a.']:
            count = (disp_lower == disp).sum()
            if count > 0:
                pct = count / total * 100
                findings.append({
                    'check': f'CAD_DISPOSITION_{disp.upper().replace(".", "")}',
                    'severity': 'INFO',
                    'detail': f'{count:,} ({pct:.1f}%)',
                })

    # Time sequence checks (§17)
    if 'time_response' in cad.columns:
        tr = pd.to_numeric(cad['time_response'], errors='coerce')
        zero_response = (tr == 0).sum()
        if zero_response > 0:
            findings.append({
                'check': 'CAD_ZERO_RESPONSE_TIME',
                'severity': 'WARNING',
                'detail': f'{zero_response:,} rows with time_response=0',
            })

    # Block_Final validation stubs (§4.1)
    if 'full_address_2' in cad.columns:
        addr = cad['full_address_2'].dropna()
        leading_amp = addr.str.startswith('& ').sum() + addr.str.startswith('&').sum()
        leading_comma = addr.str.startswith(',').sum()
        if leading_amp > 0 or leading_comma > 0:
            findings.append({
                'check': 'CAD_ADDRESS_LEADING_PUNCT',
                'severity': 'WARNING',
                'detail': f'{leading_amp} leading "&", {leading_comma} leading ","',
            })

    return findings


def check_rms(rms: pd.DataFrame, start: str, end: str) -> list[dict]:
    """Run quality checks on RMS data. Returns list of findings."""
    findings = []
    total = len(rms)
    if total == 0:
        findings.append({'check': 'RMS_EMPTY', 'severity': 'ERROR', 'detail': 'No RMS rows loaded'})
        return findings

    findings.append({'check': 'RMS_ROW_COUNT', 'severity': 'INFO', 'detail': f'{total:,} rows'})

    # CaseNumber format validation
    if 'case_number' in rms.columns:
        rms['_cn_std'] = rms['case_number'].apply(standardize_case_number)
        invalid_cn = (rms['_cn_std'] == '').sum()
        if invalid_cn > 0:
            findings.append({
                'check': 'RMS_INVALID_CASE_NUMBER',
                'severity': 'WARNING',
                'detail': f'{invalid_cn:,} rows with invalid/missing case_number (expected YY-NNNNNN)',
            })
        rms.drop(columns=['_cn_std'], inplace=True)

    # Missing IncidentType1
    if 'incident_type_1' in rms.columns:
        null_it1 = rms['incident_type_1'].isna() | (rms['incident_type_1'].str.strip() == '')
        if null_it1.any():
            findings.append({
                'check': 'RMS_NULL_INCIDENT_TYPE_1',
                'severity': 'WARNING',
                'detail': f'{null_it1.sum():,} rows with null/blank incident_type_1',
            })

    # NIBRS Classification coverage
    if 'nibrs_classification' in rms.columns:
        null_nibrs = rms['nibrs_classification'].isna() | (rms['nibrs_classification'].str.strip() == '')
        pct = null_nibrs.sum() / total * 100
        findings.append({
            'check': 'RMS_NIBRS_COVERAGE',
            'severity': 'WARNING' if pct > 20 else 'INFO',
            'detail': f'{null_nibrs.sum():,} ({pct:.1f}%) missing nibrs_classification (affects Tier 2)',
        })

    # Missing address
    if 'full_address' in rms.columns:
        null_addr = rms['full_address'].isna() | (rms['full_address'].str.strip() == '')
        pct = null_addr.sum() / total * 100
        sev = 'WARNING' if pct > 10 else 'INFO'
        findings.append({
            'check': 'RMS_MISSING_ADDRESS',
            'severity': sev,
            'detail': f'{null_addr.sum():,} ({pct:.1f}%) missing address',
        })

    # Date quality
    if 'incident_date' in rms.columns:
        dates = pd.to_datetime(rms['incident_date'], errors='coerce')
        null_dates = dates.isna().sum()
        if null_dates > 0:
            findings.append({
                'check': 'RMS_NULL_INCIDENT_DATE',
                'severity': 'WARNING',
                'detail': f'{null_dates:,} rows with unparseable incident_date',
            })

        valid_dates = dates.dropna()
        if not valid_dates.empty:
            findings.append({
                'check': 'RMS_DATE_RANGE',
                'severity': 'INFO',
                'detail': f'{valid_dates.min().date()} to {valid_dates.max().date()}',
            })

    # TotalValueStolen presence (needed for Larceny >= $500 threshold)
    if 'total_value_stolen' in rms.columns:
        non_null = rms['total_value_stolen'].notna() & (rms['total_value_stolen'].str.strip() != '')
        findings.append({
            'check': 'RMS_VALUE_STOLEN_COVERAGE',
            'severity': 'INFO',
            'detail': f'{non_null.sum():,} rows with total_value_stolen populated',
        })

    return findings


def run_preflight(args: argparse.Namespace) -> None:
    """Run all QC checks and output report."""
    log.info(f'Pre-flight QC: CAD {args.cad_pull_start} to {args.cad_pull_end}, '
             f'RMS {args.rms_pull_start} to {args.rms_pull_end}')

    cad = load_files(
        PROJECT / 'Data' / 'cad' / 'monthly',
        PROJECT / 'Data' / 'cad' / 'yearly',
        args.cad_pull_start, args.cad_pull_end,
        'report_number_new',
    )

    rms = load_files(
        PROJECT / 'Data' / 'rms' / 'monthly',
        PROJECT / 'Data' / 'rms' / 'yearly',
        args.rms_pull_start, args.rms_pull_end,
        'case_number',
    )

    cad_findings = check_cad(cad, args.cad_pull_start, args.cad_pull_end)
    rms_findings = check_rms(rms, args.rms_pull_start, args.rms_pull_end)

    # DV blocklist currency check
    dv_findings = []
    bl_path = PROJECT / 'Data' / 'dv_case_numbers_for_t4.csv'
    if bl_path.exists():
        bl = pd.read_csv(bl_path)
        max_date = bl['source_date_end'].max()
        if max_date < args.rms_pull_start:
            dv_findings.append({
                'check': 'DV_ROSTER_LAG',
                'severity': 'ERROR',
                'detail': f'Blocklist ends {max_date}, rms_pull_start={args.rms_pull_start}. HALT.',
            })
        else:
            dv_findings.append({
                'check': 'DV_BLOCKLIST_CURRENT',
                'severity': 'INFO',
                'detail': f'{len(bl):,} case numbers, through {max_date}',
            })
    else:
        dv_findings.append({
            'check': 'DV_BLOCKLIST_MISSING',
            'severity': 'ERROR',
            'detail': f'Not found: {bl_path}',
        })

    all_findings = cad_findings + rms_findings + dv_findings

    # Print report
    errors = [f for f in all_findings if f['severity'] == 'ERROR']
    warnings = [f for f in all_findings if f['severity'] == 'WARNING']

    print(f'\n{"="*60}')
    print(f'T4 Pre-flight QC Report')
    print(f'{"="*60}')
    print(f'CAD window: {args.cad_pull_start} to {args.cad_pull_end}')
    print(f'RMS window: {args.rms_pull_start} to {args.rms_pull_end}')
    print(f'Generated:  {datetime.now().isoformat()}')
    print(f'{"="*60}\n')

    for f in all_findings:
        icon = {'ERROR': '[X]', 'WARNING': '[!]', 'INFO': '[.]'}[f['severity']]
        print(f'  {icon} {f["check"]}: {f["detail"]}')

    print(f'\n{"="*60}')
    print(f'Summary: {len(errors)} errors, {len(warnings)} warnings, '
          f'{len(all_findings) - len(errors) - len(warnings)} info')
    if errors:
        print(f'HALT — resolve errors before running scoring pipeline.')
    elif warnings:
        print(f'PROCEED WITH CAUTION — review warnings in Data Quality Note.')
    else:
        print(f'ALL CLEAR — proceed to scoring.')
    print(f'{"="*60}')

    # Write JSON report
    output_dir = PROJECT / 'Output' / 'preflight'
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y_%m_%d_%H%M%S')
    report_path = output_dir / f'preflight_{ts}.json'
    report = {
        'cad_pull_start': args.cad_pull_start,
        'cad_pull_end': args.cad_pull_end,
        'rms_pull_start': args.rms_pull_start,
        'rms_pull_end': args.rms_pull_end,
        'generated': datetime.now().isoformat(),
        'findings': all_findings,
        'summary': {
            'errors': len(errors),
            'warnings': len(warnings),
            'info': len(all_findings) - len(errors) - len(warnings),
        },
    }
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    log.info(f'Report written to {report_path}')

    if errors:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='T4 CAD/RMS Pre-flight QC')
    parser.add_argument('--cad-pull-start', required=True, help='YYYY-MM-DD')
    parser.add_argument('--cad-pull-end', required=True, help='YYYY-MM-DD')
    parser.add_argument('--rms-pull-start', required=True, help='YYYY-MM-DD')
    parser.add_argument('--rms-pull-end', required=True, help='YYYY-MM-DD')
    args = parser.parse_args()
    run_preflight(args)


if __name__ == '__main__':
    main()
