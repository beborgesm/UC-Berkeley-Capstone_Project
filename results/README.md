# Results

Everything here is **derived** from [`data/`](../data/) and regenerates offline in about a
minute — no API key, no network:

```bash
make analysis      # -> analysis/ and analysis_extended/
make figures       # -> figures/
```

| Directory | What it is |
|---|---|
| [`analysis/`](analysis/) | **The headline result.** Kaplan–Meier survival, ASR@k_max with bootstrap CIs, ASR heatmaps and the pre-registered log-rank tests, over the balanced 3-model benchmark (480 runs, 24 cells). Start at [`analysis/REPORT.md`](analysis/REPORT.md). |
| [`analysis_extended/`](analysis_extended/) | **Appendix.** The same analysis over the full raw collection (523 runs, 27 cells), adding the partially-collected `gpt-4-turbo`. Run against the frozen pre-registration config, so it reports **all five** declared hypotheses with their disposition. |
| [`figures/`](figures/) | The 14-figure slide-ready gallery (Plotly) + [`figures/FIGURES.md`](figures/FIGURES.md), a captioned index saying what each figure shows and which slide it suits. |

## Headline numbers

- **480 survival trials** · 24 cells · k_max = 10 rounds · **181 breaches / 299 held**
- Attack success rate at 10 rounds:
  **`gpt-3.5-turbo` 92%** (2023) · **`gpt-5-nano` 14%** (2025) · **`gpt-4o-mini` 8%** (2024)
- **The twist:** the newest and smallest model is *more* breakable than the year-older,
  more capable one — capability, not recency, drives robustness.
- Both computable pre-registered log-rank pairs separate at **p < 0.001**.
- **0 administratively censored runs** — every censored observation is a genuine survival to
  `k_max`, not an infrastructure failure.

Every breach above was decided by deterministic code (canary reappearance or a real tool
invocation). The LLM Judge is a secondary, non-authoritative signal and can never define a
breach; its figures are labelled as such.

## Two reports, on purpose

`analysis/` is the benchmark: a fully balanced grid where every cell has N=20, so the models
are compared on equal footing. `analysis_extended/` exists so the partially-collected 4th
model isn't silently dropped — it reports `gpt-4-turbo`'s two complete cells and marks the
two hypotheses naming the never-collected `o4-mini` as `NOT_COLLECTED` rather than deleting
them. See [`docs/PREREGISTRATION.md`](../docs/PREREGISTRATION.md).
