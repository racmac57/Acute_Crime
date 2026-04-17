"""Emit HTML + CSV for top N locations from score_integration output."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored-csv", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--cycle-id", default="T4_C01W02")
    ap.add_argument("--top-n", type=int, default=5)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.scored_csv)
    df = df.sort_values("weighted_score", ascending=False).reset_index(drop=True)
    top = df.head(args.top_n).copy()
    top.insert(0, "rank", range(1, len(top) + 1))
    top["SingleLine"] = top["location"].astype(str).str.replace('"', "", regex=False)

    top.to_csv(args.out_dir / f"{args.cycle_id}_top{args.top_n}_hotspots_for_arcgis.csv", index=False)

    meta = {
        "cycle_id": args.cycle_id,
        "source_scored_locations": str(args.scored_csv),
        "top_n": args.top_n,
        "note": (
            "Geocode SingleLine or location in ArcGIS Pro; symbolize by rank or weighted_score."
        ),
    }
    (args.out_dir / f"{args.cycle_id}_top{args.top_n}_hotspots_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    rows = []
    for _, r in top.iterrows():
        addr = str(r["location"]).strip('"')
        q = quote(addr)
        map_href = f"https://www.google.com/maps/search/?api=1&query={q}"
        rows.append(
            f"""<tr>
    <td class="rank">{int(r["rank"])}</td>
    <td class="addr">{esc(addr)}</td>
    <td class="num">{r["weighted_score"]:.2f}</td>
    <td class="num">{r["tier1_sum"]:.2f}</td>
    <td class="num">{r["tier2_sum"]:.2f}</td>
    <td class="num">{int(r["rms_part1_count"])}</td>
    <td><a href="{map_href}" target="_blank" rel="noopener">Map</a></td>
</tr>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>T4 Top {args.top_n} Citywide Hotspot Locations</title>
<style>
:root {{ --navy: #0d233c; }}
body {{ margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #e5e7eb; color: #222; }}
.shell {{ max-width: 960px; margin: 16px auto; background: #fff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,.08); padding: 20px 24px; }}
.header {{ border-bottom: 3px solid var(--navy); padding-bottom: 10px; margin-bottom: 16px; }}
.eyebrow {{ font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: #555; }}
h1 {{ margin: 0; font-size: 22px; color: var(--navy); text-transform: uppercase; letter-spacing: .04em; }}
.sub {{ font-size: 13px; color: #444; margin-top: 6px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #ddd; vertical-align: top; }}
th {{ background: var(--navy); color: #fff; font-weight: 600; }}
.rank {{ width: 36px; font-weight: 700; color: var(--navy); }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.note {{ margin-top: 18px; font-size: 11px; color: #444; line-height: 1.45; }}
@media print {{ body {{ background: #fff; }} .shell {{ box-shadow: none; }} }}
</style>
</head>
<body>
<div class="shell">
  <div class="header">
    <div class="eyebrow">Hackensack Police Department · T4</div>
    <h1>Top {args.top_n} hotspot locations (citywide)</h1>
    <div class="sub">Cycle <strong>{args.cycle_id}</strong> · Ranked by <code>weighted_score</code>
    (DV-filtered RMS + Tier 1 CAD). Location key = raw address text.</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Location</th><th>Weighted score</th><th>Tier 1 sum</th><th>Tier 2 sum</th><th>RMS Part 1</th><th>Quick map</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>
  <p class="note">
    <strong>ArcGIS Pro:</strong> import <code>{args.cycle_id}_top{args.top_n}_hotspots_for_arcgis.csv</code> — geocode
    <code>SingleLine</code>, symbolize by rank. <strong>Reference assets</strong> (DV layouts, sample CSVs, .aprx):
    <code>Imported_from_sandbox/dv_doj_arcgis_exports/</code>. <strong>Map</strong> links are public basemap search only.
  </p>
</div>
</body>
</html>
"""
    out_html = args.out_dir / f"{args.cycle_id}_top{args.top_n}_hotspots_citywide.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"Wrote {out_html}")


if __name__ == "__main__":
    main()
