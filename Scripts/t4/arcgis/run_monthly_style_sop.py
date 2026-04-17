"""
Run the monthly ArcGIS style-transfer SOP in one command.

Flow:
1) export_layer_styles.py
2) apply_layer_styles.py
3) validate_layer_styles.py
4) build pass/fail run snapshot artifacts

This script is designed for ArcGIS Pro `propy` or Python window `exec(...)`.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import importlib.util
import json
import traceback

import arcpy

PROJECT_ROOT = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\10_Projects\Acute_Crime")
OUT_DIR = PROJECT_ROOT / "_overnight" / "arcgis_style_transfer"
RUN_JSON = OUT_DIR / "monthly_sop_run_report.json"
RUN_MD = OUT_DIR / "monthly_sop_run_report.md"
APPLY_SUMMARY = OUT_DIR / "style_apply_summary.json"
VALIDATION_JSON = OUT_DIR / "style_validation_report.json"
EXPORT_SUMMARY = PROJECT_ROOT / "Scripts" / "t4" / "arcgis" / "styles" / "export_summary.json"
SCRIPTS_DIR = PROJECT_ROOT / "Scripts" / "t4" / "arcgis"

POLICY_GUARDRAILS = [
    "Tier A = high confidence + risk >= 0.70",
    "Tier B = high/medium confidence + risk 0.55-0.69",
    "Tier C = watchlist only",
    "Downtrend downgrade requires 2 down cycles + supervisor validation",
    "Overlay scope remains top 50",
    "Confidence calibration deferred to next cycle",
]


def log(msg: str) -> None:
    print(msg)
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass


def current_project_available() -> bool:
    try:
        _aprx = arcpy.mp.ArcGISProject("CURRENT")
        del _aprx
        return True
    except Exception:
        return False


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run_step(module_name: str) -> dict:
    step = {
        "module": module_name,
        "status": "not_run",
        "error": "",
    }
    try:
        module_path = SCRIPTS_DIR / f"{module_name}.py"
        if not module_path.exists():
            raise FileNotFoundError(f"Step script not found: {module_path}")
        spec = importlib.util.spec_from_file_location(module_name, str(module_path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load module spec for {module_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Use CURRENT when running inside ArcGIS Pro GUI; fall back to file mode
        # for headless/scheduled propy runs.
        if hasattr(mod, "USE_CURRENT_PROJECT"):
            setattr(mod, "USE_CURRENT_PROJECT", current_project_available())
        mod.main()
        step["status"] = "pass"
        log(f"[PASS] {module_name}")
    except Exception as exc:
        step["status"] = "fail"
        step["error"] = f"{type(exc).__name__}: {exc}"
        log(f"[FAIL] {module_name} -> {step['error']}")
    return step


def evaluate_outputs() -> dict:
    export_summary = load_json(EXPORT_SUMMARY)
    apply_summary = load_json(APPLY_SUMMARY)
    validation_summary = load_json(VALIDATION_JSON)

    export_pass = bool(export_summary) and int(export_summary.get("exported_layer_count", 0)) > 0

    apply_rows = apply_summary.get("result_rows", [])
    apply_failures = [
        row for row in apply_rows if row.get("status") not in {"applied", "applied_from_source_layer_fallback"}
    ]
    apply_pass = bool(apply_rows) and not apply_failures

    validation_rows = validation_summary.get("results", [])
    validation_failures = [row for row in validation_rows if row.get("status") != "pass"]
    validation_pass = bool(validation_rows) and not validation_failures

    return {
        "export": {
            "status": "pass" if export_pass else "fail",
            "exported_layer_count": export_summary.get("exported_layer_count", 0),
            "error_layer_count": export_summary.get("error_layer_count", 0),
        },
        "apply": {
            "status": "pass" if apply_pass else "fail",
            "mapped_layer_count": len(apply_rows),
            "failure_count": len(apply_failures),
        },
        "validate": {
            "status": "pass" if validation_pass else "fail",
            "mapped_layer_count": len(validation_rows),
            "failure_count": len(validation_failures),
        },
    }


def write_reports(step_runs: list[dict], checks: dict) -> dict:
    overall_status = "pass" if all(s["status"] == "pass" for s in step_runs) and all(
        c.get("status") == "pass" for c in checks.values()
    ) else "fail"

    report = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "overall_status": overall_status,
        "steps": step_runs,
        "checks": checks,
        "policy_guardrails_confirmed": POLICY_GUARDRAILS,
    }
    RUN_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_lines = [
        "# Monthly ArcGIS Style SOP Run Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Overall status: **{report['overall_status'].upper()}**",
        "",
        "## Step Execution",
        "",
        "| Step | Status | Error |",
        "|---|---|---|",
    ]
    for step in step_runs:
        md_lines.append(f"| {step['module']} | {step['status']} | {step.get('error', '')} |")

    md_lines.extend(
        [
            "",
            "## Output Checks",
            "",
            "| Check | Status | Details |",
            "|---|---|---|",
            (
                f"| export_summary | {checks['export']['status']} | "
                f"exported={checks['export']['exported_layer_count']}, "
                f"errors={checks['export']['error_layer_count']} |"
            ),
            (
                f"| apply_summary | {checks['apply']['status']} | "
                f"mapped={checks['apply']['mapped_layer_count']}, "
                f"failures={checks['apply']['failure_count']} |"
            ),
            (
                f"| validation_summary | {checks['validate']['status']} | "
                f"mapped={checks['validate']['mapped_layer_count']}, "
                f"failures={checks['validate']['failure_count']} |"
            ),
            "",
            "## Policy Guardrails (Carry-forward)",
            "",
        ]
    )
    for rule in POLICY_GUARDRAILS:
        md_lines.append(f"- {rule}")

    RUN_MD.write_text("\n".join(md_lines), encoding="utf-8")
    return report


def main() -> None:
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        step_runs: list[dict] = []
        for module_name in ("export_layer_styles", "apply_layer_styles", "validate_layer_styles"):
            step = run_step(module_name)
            step_runs.append(step)
            if step["status"] != "pass":
                break

        checks = evaluate_outputs()
        report = write_reports(step_runs, checks)
        log(f"[OK] Run JSON: {RUN_JSON}")
        log(f"[OK] Run MD: {RUN_MD}")
        if report["overall_status"] != "pass":
            raise RuntimeError("Monthly style SOP run ended in FAIL status.")
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
        raise
    except Exception as exc:
        print(f"Python error: {exc}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
