# Next-Cycle Kickoff Checklist — Persistent Hotspots

## 1) Preflight Data Checks
- Confirm CAD and RMS source files exist for the new cycle window.
- Run zero-byte check on incoming exports before processing.
- Confirm DV blocklist freshness and source-date coverage.
- Confirm date horizon and analysis anchor are set correctly.

## 2) Run Refresh Command
- From repo root, execute:
  - `python -m Scripts.t4.persistent_hotspots`
- Confirm run completes without blocker files.

## 3) Validation Checks
- Verify top-10 row count and required columns in citywide output.
- Verify command brief top-10 table matches CSV order/scores.
- Verify confidence flags and temporal windows are populated.
- Verify known caveat lines are present in command and technical docs.

## 4) Deliverable Refresh Steps
- Refresh:
  - `Docs/deliverables/T4_persistent_hotspots_citywide.csv`
  - `Docs/deliverables/T4_persistent_hotspots_command_staff.md`
  - `Docs/deliverables/T4_persistent_hotspots_technical_appendix.md`
- Archive any prior-cycle copies only after verification pass.

## 5) Briefing Refresh Steps
- Update command email body from latest top-3 hotspots/windows.
- Update verbal brief with current top-3 and confidence framing.
- Keep wording as historical risk patterning for targeted patrol allocation.

## 6) Post-Run Caveat Review
- Re-check whether `trend_90d` reflects seasonal/context effects.
- Re-check status of spatial enrichment (`Post`, `PDZone`, `Grid`, lat/lon).
- Re-check RMS anomaly status (zero-byte stubs or re-export notes).
- Document all caveats before command distribution.

# Next-Cycle Kickoff Checklist — Persistent Hotspots Refresh

**Owner:** Analyst on duty at SSOCC.
**Purpose:** Repeatable kickoff for the next persistent-hotspot cycle. Run top-to-bottom; do not skip validation.

---

## 1. Preflight Data Checks

- [ ] Confirm `run_date`, `cycle_id`, `analysis_date`, `cad_pull_start/end`, `rms_pull_start/end` are populated per CLAUDE.md Section 0. If any blank — **halt**.
- [ ] Verify CAD monthly exports exist for every month in the horizon under `Data/cad/monthly/` and `Data/cad/yearly/`. No gaps.
- [ ] Verify RMS monthly exports exist for every month under `Data/rms/monthly/` and `Data/rms/yearly/`.
- [ ] **Zero-byte check:** every `.xlsx` input must be > 50 KB. Flag and re-export any file under that size (reference: the Feb 2026 RMS 0-byte stub incident, resolved 2026-04-16).
- [ ] DV blocklist freshness: open `Data/dv_case_numbers_for_t4.csv`; confirm `source_date_end` max covers the full `rms_pull_end` window. If lagging, regenerate `backfill_dv` and the supplemental PDF extraction before proceeding.
- [ ] DV roster lag check: after blocklist loads, confirm roster coverage meets or exceeds `rms_pull_start`. If not — **halt and flag** `[DV ROSTER LAG — regenerate backfill_dv before proceeding]`.
- [ ] Confirm `Data/dv_case_numbers_for_t4.csv` has not shrunk vs prior cycle (row count floor = prior cycle row count).

## 2. Run Command

- [ ] From project root, run:

  ```
  python -m Scripts.t4.persistent_hotspots
  ```

- [ ] Watch console for DV exclusion counts (rows excluded by `dv_case_match` and `type_fallback`) and filtered CAD/RMS totals. Capture these for the Data Quality Note.

## 3. Validation Checks

- [ ] Confirm outputs regenerated:
  - `Docs/deliverables/T4_persistent_hotspots_citywide.csv` (top 10)
  - `Docs/deliverables/T4_persistent_hotspots_command_staff.md`
  - `Docs/deliverables/T4_persistent_hotspots_technical_appendix.md`
  - `_overnight/persistent_hotspots/T4_persistent_hotspots_full_citywide.csv` (full 700+)
- [ ] Spot-check top-3 locations against raw CAD: do `Incident` types match the severity rule (shots fired / aggravated assault / fight / disturbance / suspicious)?
- [ ] `persistent_risk_score` range is [0, 1] and descending. No negatives, no duplicates in `location_key`.
- [ ] No row has `confidence_band = low` in the top 10. Low-confidence rows are appendix only.
- [ ] Address normalization sanity: scan for `"& "` leading or `"0 block "` with missing street name; flag any.
- [ ] Citywide location count is in the expected band (roughly 600-900 for a 2-year horizon). Sharp movement means a filter changed.
- [ ] DV exclusion counts are non-zero on both layers (`dv_case_match` and `type_fallback`).

## 4. Deliverable Refresh

- [ ] Update horizon and analysis date in the first lines of the command-staff briefing `.md`.
- [ ] Update the top-10 table (`Risk`, `Incidents`, `Months Active`, `Trend 90d`, `Confidence`).
- [ ] Update the Deployment Windows table (top DOW, top time window, day-of-month band, weekend share).
- [ ] Update the event-count footer line (`Generated from N CAD + M RMS events across K locations`).
- [ ] In the technical appendix, update horizon/analysis-date header, inputs list, DV blocklist row count, and DV exclusion counts.
- [ ] Reconfirm the caveat list against the new run — especially the `trend_90d` interpretation for the new anchor date.

## 5. Briefing Refresh

- [ ] Regenerate the command-staff email body from the new top 3 (location / top DOW / top time window / day-of-month band).
- [ ] Regenerate the 60-second verbal brief with the new top 3.
- [ ] Confirm subject line reflects the new cycle ID.

## 6. Post-Run Caveat Review

- [ ] Re-read the `trend_90d` caveat against the new analysis date — confirm seasonal framing still applies; adjust wording if the compare window crosses a season.
- [ ] Confirm the "spatial enrichment deferred" caveat is still accurate. If Post/PDZone/Grid/lat-lon has been joined, remove the caveat and document the join method in the appendix.
- [ ] Re-read the DV roster-lag caveat; update the cited `source_date_end` max.
- [ ] Re-read the "RMS zero-byte stub resolved" caveat. If further anomalies surfaced this cycle, add them to `Docs/data_gaps.md` and reference here.
- [ ] Confirm no "predictive policing" phrasing slipped in. Use "historical risk patterning" and "targeted patrol allocation."
- [ ] Confirm `cycle_id` is populated on every deliverable filename or header where applicable.

## 7. Handoff

- [ ] File new handoff under `Docs/handoffs/handoff_YYYYMMDD_persistent_hotspots_<cycle_id>.md`.
- [ ] Do not commit/push until explicitly authorized.
