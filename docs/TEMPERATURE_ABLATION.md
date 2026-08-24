# Temperature ablation — 0.7 vs 1.0

The published benchmark runs at **target temperature 1.0**. An earlier, complete generation
ran at **0.7**. This note records why the setting changed and the evidence that it didn't move
the result — so "we switched temperature midway" is a documented robustness check rather than
an unexplained inconsistency.

## Why it changed

Temperature is a nuisance parameter here, not a variable of interest: it must be **constant
across the roster** or between-model comparisons stop meaning anything.

When the roster was extended to include GPT-5 / o-series models, that constraint bit. Those
endpoints accept only their default temperature (1.0) and reject any explicit value. So there
were exactly two options:

1. keep 0.7 and exclude every newer model — which would have deleted the
   "capability vs recency" axis that turned out to be the project's most interesting finding; or
2. standardise the whole roster at 1.0 and re-collect.

We chose (2), and re-ran every cell rather than pooling two temperature regimes.

## Evidence it was safe

Before committing to the re-run, the 0.7 generation was compared against the 1.0 generation on
the two models present in both. Same grid (2 boundaries × 4 vectors × 20 repetitions,
k_max = 10), same attacker, same detection — only the temperature differs.

| Model | temp 0.7 | temp 1.0 | Δ |
|---|---|---|---|
| `gpt-3.5-turbo` | 147 / 160 breached (**91.9%**) | 147 / 160 breached (**91.9%**) | **0** |
| `gpt-4o-mini` | 7 / 160 breached (**4.4%**) | 12 / 160 breached (**7.5%**) | +5 breaches |

`gpt-3.5-turbo` is *identical* — the same 147 of 160 runs breached at both settings.
`gpt-4o-mini` moved by 5 breaches out of 160; at that rate the bootstrap CIs overlap heavily
and the shift is well within sampling noise for N=160. Crucially, neither the **ranking** nor
the **order of magnitude** changes: the weak model breaks ~92% of the time at either setting,
the robust one breaks under 10% at either setting.

Higher temperature would, if anything, be expected to *help* the attacker slightly (more
varied targets sampling further from their safest response), and the small `gpt-4o-mini` move
is in that direction. Nothing in the conclusions depends on it.

## What that means for the published results

- **No result mixes temperatures.** Everything in [`data/`](../data/) and
  [`results/`](../results/) is the temperature-1.0 generation.
- The 0.7 generation was **not deleted** — 320 runs and 644 transcripts are retained offline.
  They are not published because they are superseded, not because they disagree.
- The change is logged as a dated protocol amendment in
  [`PREREGISTRATION.md`](PREREGISTRATION.md) §3A.

## Reproducing this table

The comparison is a straight projection of each generation's `rounds.csv` to per-run survival
outcomes:

```python
from breachbench.recording.run_summary import rounds_df_to_run_summary
import pandas as pd

df = rounds_df_to_run_summary(pd.read_csv(rounds_csv, low_memory=False))
df = df[df.run_valid == 1]
df.groupby("target_model_version").event_observed.agg(["size", "sum"])
```

Run it against `data/rounds_benchmark.csv` for the 1.0 column. The 0.7 column needs the
retained offline archive; ask if you want it.
