# Data sourcing and licensing

## Source

All point-level data and the clutch scores come from the **Match Charting Project (MCP)**,
compiled by Jeff Sackmann and volunteer contributors:
https://github.com/JeffSackmann/tennis_MatchChartingProject

Raw MCP files are not redistributed in this repository. Every script that
needs them fetches them at run time from `raw.githubusercontent.com`, pinned to
one upstream commit (below). The data behind every reported number is therefore
a public GitHub repository at an exact, checkable snapshot, plus the derived
per-player CSVs committed here. See the root `README.md` "Reproduce" section
for the exact files and commands.

## Pinned snapshot used in the paper

- Upstream repository: https://github.com/JeffSackmann/tennis_MatchChartingProject
- Commit: `2c59eef194967e688b69e73df344184a06322cd8` ("thru 25 may 2026",
  committed 2026-05-25). The eight raw files used (ATP and WTA matches plus
  three points files each) were downloaded 2026-07-07 and verified to be
  byte-identical to that commit: each local file's git blob hash equals the
  hash in that commit's tree.
- `DATA_MANIFEST.csv` records each file's size, SHA-256, git blob hash and the
  commit-pinned source URL, so a fresh download can be checked with
  `sha256sum` or `git hash-object`.
- The Match Charting Project is updated continuously, so fetching from
  `master` later will give different data (and slightly different numbers);
  use the pinned URLs to reproduce the paper.

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

## Tour-level match results (Section 4.6 and Table S18 only)

The external-criterion check uses tour-level match results (winner, loser, set scores, best-of, tournament date) for ATP and WTA,
1968 to 2026-05-25, from Jeff Sackmann's `tennis_atp` and `tennis_wta` (CC BY-NC-SA 4.0). The upstream repositories were no longer
reachable at `github.com/JeffSackmann` when the check was run, so `src/robustness/fetch_tour_results.py` fetches the yearly files
from an archival mirror, `github.com/Aneeshers/tennis-sackmann-archive`, at commit `83733587353df8a41f2fd4f516147d5aa83f5a8d`
(made 2026-06-25 from upstream commits of June 2026), and checks each file against `DATA_MANIFEST.csv`. The files are written to
`results/tour_results/` and are not committed. The mirror is a third-party copy; its integrity was tested against the charted data
(the winner of the last charted point equals the file's winner in 99.75% of WTA and 99.86% of ATP charted matches whose chart reaches
match point). Same license terms as the MCP data.
