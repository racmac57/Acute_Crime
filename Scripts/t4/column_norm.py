"""
Column normalization for T4 pipeline.
Handles both spaced (RMS export) and camelCase (master prompt) variants.
"""
import re
import pandas as pd


def to_snake_case(name: str) -> str:
    """Convert any column name variant to snake_case."""
    s = str(name).strip()
    # Insert underscore before uppercase letters preceded by lowercase
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    # Replace spaces, hyphens, dots with underscore
    s = re.sub(r'[\s\-\.]+', '_', s)
    # Collapse multiple underscores
    s = re.sub(r'_+', '_', s)
    return s.lower().strip('_')


# Alias map: known variants -> canonical snake_case
# Covers RMS exports (spaces), master prompt (camelCase), and T4 workbook (mixed)
COLUMN_ALIASES = {
    'case number':          'case_number',
    'casenumber':           'case_number',
    'incident type_1':      'incident_type_1',
    'incidenttype1':        'incident_type_1',
    'incident type_2':      'incident_type_2',
    'incidenttype2':        'incident_type_2',
    'incident type_3':      'incident_type_3',
    'incidenttype3':        'incident_type_3',
    'incident date':        'incident_date',
    'incidentdate':         'incident_date',
    'incident time':        'incident_time',
    'incidenttime':         'incident_time',
    'report date':          'report_date',
    'reportdate':           'report_date',
    'report time':          'report_time',
    'reporttime':           'report_time',
    'fulladdress':          'full_address',
    'fulladdress2':         'full_address_2',
    'how reported':         'how_reported',
    'howreported':          'how_reported',
    'time of call':         'time_of_call',
    'timeofcall':           'time_of_call',
    'time dispatched':      'time_dispatched',
    'timedispatched':       'time_dispatched',
    'time out':             'time_out',
    'timeout':              'time_out',
    'time in':              'time_in',
    'timein':               'time_in',
    'time spent':           'time_spent',
    'timespent':            'time_spent',
    'time response':        'time_response',
    'timeresponse':         'time_response',
    'response type':        'response_type',
    'responsetype':         'response_type',
    'cadnotes':             'cad_notes',
    'pdzone':               'pd_zone',
    'zonecalc':             'pd_zone',
    'reportnumbernew':      'report_number_new',
    'total value stolen':   'total_value_stolen',
    'totalvaluestolen':     'total_value_stolen',
    'total value recover':  'total_value_recover',
    'totalvaluerecover':    'total_value_recover',
    'officer of record':    'officer_of_record',
    'officerofrecord':      'officer_of_record',
    'nibrs classification': 'nibrs_classification',
    'nibrsclassification':  'nibrs_classification',
    'case_status':          'case_status',
    'det_assigned':         'det_assigned',
    'completecalc':         'complete_calc',
    'reviewed by':          'reviewed_by',
    'reviewedby':           'reviewed_by',
    'dayofweek':            'day_of_week',
    'hourminuetscalc':      'hour_minuets_calc',
    'hour minuets calc':    'hour_minuets_calc',
    'cyear':                'c_year',
    'cmonth':               'c_month',
    'reg state 1':          'reg_state_1',
    'regstate1':            'reg_state_1',
    'reg state 2':          'reg_state_2',
    'regstate2':            'reg_state_2',
    'incident date_between': 'incident_date_between',
    'incident time_between': 'incident_time_between',
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize all column names to snake_case with alias resolution."""
    new_cols = {}
    for col in df.columns:
        lower = str(col).strip().lower()
        if lower in COLUMN_ALIASES:
            new_cols[col] = COLUMN_ALIASES[lower]
        else:
            new_cols[col] = to_snake_case(col)
    return df.rename(columns=new_cols)


def standardize_case_number(val) -> str:
    """
    Normalize a case number to YY-NNNNNN format.
    Mirrors backfill_dv.py standardise_case_number() contract.
    """
    if pd.isna(val):
        return ''
    s = str(val).strip().upper()
    s = re.sub(r'[^0-9A-Z\-]', '', s)
    if re.match(r'^\d{2}-\d{6}([A-Z])?$', s):
        return s
    return ''
