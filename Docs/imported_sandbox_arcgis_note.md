# Sandbox ArcGIS package (local disk only)

A full copy of `C:\_Sandbox\02_ETL_Scripts\dv_doj\arcgis_exports` exists under **`Imported_from_sandbox/dv_doj_arcgis_exports/`** in this project folder (including **`dv_doj\dv_doj.aprx`**, **`dv_doj.gdb`**, **`dv_incidents_for_arcgis.csv`**, layouts, PDFs, and helper scripts). It was mirrored on **2026-04-16** with **`robocopy`** excluding **`GpMessages`**.

The **`Imported_from_sandbox/`** tree is **gitignored** (large GDB / exports). To refresh the OneDrive canonical repo (`02_ETL_Scripts\dv_doj\arcgis_exports`), run a similar `robocopy` from Sandbox → OneDrive when ready.

**T4 deliverables** (HTML + ArcGIS table): **`Docs/deliverables/T4_C01W02_top5_hotspots_*`** — top five **T4** locations from `score_integration`, not the DV layer.
