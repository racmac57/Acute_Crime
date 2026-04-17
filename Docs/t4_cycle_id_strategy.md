# T4 Cycle ID Strategy — Closed Decision (2026-04-16)

## Problem

`T4_Master_Reporting_Template.xlsx` (path in **CLAUDE.md §3**) inspection found `ReportName` = **`T4_Current` only** — no `T4_C01W02`-style strings in the workbook. The [master prompt](../T4_Hotspot_Analysis_Master_Prompt_v3.md) still expects human-readable cycle labels for outputs.

## Decision (operator + build)

| Field | Authoritative source | Notes |
|-------|----------------------|--------|
| `cycle_id` | **Section 0 run parameters** (same naming as `T4_Master.xlsx` / `ReportName` *process* — e.g. `T4_C01W02`) | Entered by the analyst from **`T4_Master.xlsx`** (Excel file used for scheduling) or command’s published cycle calendar — **not** read from `T4_Master_Reporting_Template.xlsx` `ReportName` until that column is populated with structured IDs. |
| `cycle_7day`, `cycle_28day` | **Section 0 run parameters** | Must be populated before scoring/output per master prompt §0 / §11. |
| `ReportName` in reporting workbook | **Context only** | May remain `T4_Current` for dashboard slices; **does not** drive pipeline labels. |

This is **option (b)** from the plan: *generate / supply cycle IDs via run parameters and command naming convention*, with **option (a)** — a separate **cycle calendar** file (YAML/CSV) — allowed later if SSOCC wants date-range → ID lookup in code.

## Pipeline rules

1. **Validate:** If `cycle_id` is blank, **halt** (master prompt §0).
2. **Do not** infer `cycle_id` from `T4_Master_Reporting_Template.xlsx` alone until sheet/column definitions are extended by the org.
3. **Optional future:** Add `config/t4_cycle_calendar.yaml` (start_date, end_date → `cycle_id`) and load if present; otherwise Section 0 remains sole source.

## Related

- [CLAUDE.md §4a](../CLAUDE.md) — workbook column inventory.
- [Docs/plans/t4_rms_dv_filtering_d5a59b9b.plan.md](plans/t4_rms_dv_filtering_d5a59b9b.plan.md) — todo `t4-cycle-id-strategy`.
