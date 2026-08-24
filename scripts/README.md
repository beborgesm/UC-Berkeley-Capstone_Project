# scripts/

Most of these have a `make` target — see the [Makefile](../Makefile). Everything here runs
offline against the committed dataset **except** `judge_transcripts.py`, which is the only
script that needs a live API key.

| Script | `make` | What it does |
|---|---|---|
| `verify_dataset.py` | `make verify` | Asserts `data/` still matches its documented state: per-cell N, breach/censor totals, zero admin-censoring, transcript↔CSV coverage (including the 24 documented orphans), Judge coverage. Exits non-zero on drift. Runs in CI — the dataset can't be regenerated, so this is the guard. |
| `make_benchmark_subset.py` | `make subset` | Derives `data/rounds_benchmark.csv` from `data/rounds_raw.csv` by keeping only the cells the roster in `config/experiment.yaml` can produce. Matches on the stable configured `cell_id`, never on resolved model names (those drift). |
| `make_figures.py` | `make figures` | The 14-figure slide-ready Plotly gallery → `results/figures/`. Primary figures always render; the secondary Judge panels render if the judge CSV exists, and print their coverage. Needs a headless Chromium (kaleido). |
| `judge_transcripts.py` | `make judge` | **SECONDARY, needs `GEMINI_API_KEY`.** Post-hoc Judge pass over saved transcripts → `judge_scores.csv`. Resumable, incremental, seeded-shuffle (a partial pass stays balanced), graceful-stop on repeated provider failures. The published scores are already committed, so this is optional. |
| `run_experiment.py` · `pilot.py` · `analyze.py` | — | Thin wrappers around the console entry points (`breachbench-run` / `-pilot` / `-analyze`), for running without `pip install -e .`. Identical behaviour and flags. |

## Adding data to the published set

Live collection writes to `output/` and `runs/`, never to `data/`. To promote a new
collection: copy the CSVs and transcripts into `data/`, re-run `make subset`, then
`make reproduce`, and confirm `make verify` still passes (update the expected counts in
`verify_dataset.py` if the grid genuinely changed).
