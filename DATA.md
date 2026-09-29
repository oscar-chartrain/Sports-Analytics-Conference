# Data sourcing and licensing

## Source

All match and point-level data comes from the **Match Charting Project (MCP)**,
compiled by Jeff Sackmann and volunteer contributors:
https://github.com/JeffSackmann/tennis_MatchChartingProject

Nothing from that project is redistributed in this repository. Every script
that needs MCP data fetches it fresh, at run time, directly from
`raw.githubusercontent.com`. See the root `README.md` "Reproduce" section for
the exact files and commands.

## License of the underlying MCP data

The Match Charting Project's data is licensed **CC BY-NC-SA 4.0**
(Attribution-NonCommercial-ShareAlike):
https://creativecommons.org/licenses/by-nc-sa/4.0/

That means:
- Any use of the raw MCP data (or anything substantially derived from it)
  must credit the Match Charting Project.
- Non-commercial use only.
- Derivatives must be shared under the same license.

This repository's own `LICENSE` file (MIT) covers the code only: the
pipeline scripts, the shared modules, the analysis logic. It doesn't
relicense the MCP data itself, and nothing here should be read as claiming
broader rights over MCP data than MCP's own license grants. The small
derived CSVs in `results/` (see below) carry the CC BY-NC-SA terms with
them, since they're built directly from MCP data.

## What is and isn't in this repo

**Not included, by design:**
- Raw MCP CSVs (`charting-*-matches.csv`, `charting-*-points-*.csv`): these
  are fetched fresh by the pipeline, not committed. They're re-fetched because
  MCP updates periodically (~every 100 new charted matches), so a static copy
  would go stale; fetching fresh also avoids any ambiguity about
  redistributing MCP's licensed data ourselves.
- Point-level intermediate files (e.g. a full per-point leverage table is
  ~1.1M rows / ~200MB): regeneratable from the raw data via the pipeline,
  not sensible to ship as a repo artifact.
- `cache_*.pkl` extraction caches used by the full-pool staged driver
  (`src/entropy_extraction_stage1.py` → `src/stage2_assemble_features.py`):
  local, disposable, regenerated on demand.

**Included:**
- Small, final per-player feature/output CSVs in `results/` (tens of KB):
  one row per player, already aggregated. These are derived from MCP data and
  inherit its CC BY-NC-SA terms.
- All pipeline code, in full.

## Reproducing the raw pulls yourself

See the root `README.md`'s "Reproduce" section for the exact `curl` commands
and file names needed for both ATP (`m`) and WTA (`w`) data across all three
decade files.
