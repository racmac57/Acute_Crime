# DV case blocklist — refresh governance

**Production file:** `Data/dv_case_numbers_for_t4.csv` (PII-safe: `case_number`, `source`, `source_date_end`).

## When to refresh

1. After a new **`dv_doj`** `dv_final_enriched` build that extends past the current `source_date_end`.
2. After a new **DV roster PDF** (or other official supplement) is released — extract case numbers and merge, deduplicate, document in `CHANGELOG`.

## How

1. Do **not** copy full `dv_final_enriched.csv` into Acute_Crime (PII). Append only new `case_number` rows or rebuild from approved extracts.
2. Update **`source`** and **`source_date_end`** columns to reflect provenance.
3. Run row-count / spot checks against RMS if needed.

**Owner:** Principal Analyst (SSOCC) or delegate per `dv_doj/docs/pii_policy.md`.
