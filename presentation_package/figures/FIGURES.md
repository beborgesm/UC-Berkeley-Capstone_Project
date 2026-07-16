# BreachBenchmark — Figure Gallery (for the slide deck)

All figures are high-res PNGs in this folder, rendered with **Plotly** (clean, modern,
consistent design). One fixed palette is used across **every** figure:

**`gpt-3.5-turbo` = orange · `gpt-5-nano` = amber · `gpt-4o-mini` = green**
(and for the Judge: No-degradation = green · Weak-refusal = amber · Persona-break = orange.)

Generated from the clean 3-model temperature-1.0 dataset. There are more figures here than a
deck needs — pick the strongest.

---

## Headline numbers (say these out loud)

- **480 survival trials** · 24 cells (3 models × 2 boundaries × 4 attack vectors × 20 reps) · k_max = 10 rounds.
- **181 breaches / 299 held.** Overall attack success rate (ASR@k=10):
  - `gpt-3.5-turbo` (2023): **92%** — 147/160
  - `gpt-5-nano` (2025): **14%** — 22/160
  - `gpt-4o-mini` (2024): **8%** — 12/160
- **The twist:** the *newest, tiniest* model (gpt-5-nano, 2025) is **more breakable** than the older gpt-4o-mini (2024). **Capability, not recency, drives robustness.**
- **Log-rank (pre-registered):** both computable pairs separate with **p < 0.001** (below).
- Every breach is deterministic (canary reappearance / real tool invocation); the LLM Judge is secondary and never defines a breach.

---

## PRIMARY figures (deterministic — the core results)

| File | What it shows | Best for |
|---|---|---|
| **fig_asr_by_model.png** | Headline bar: overall ASR per model (92 / 14 / 8%) with bootstrap 95% CI. | **Title / results slide.** The one-glance headline. |
| **fig_km_by_model.png** | Kaplan–Meier survival curves, one per model (pooled over all vectors). gpt-3.5 collapses by round 2; the others plateau high. | **The "survival analysis" slide** — method + separation at once. |
| **fig_capability_vs_recency.png** | Robustness vs release year. 2024 gpt-4o-mini sits above 2025 gpt-5-nano. | **The "newer ≠ safer" insight slide** — your most surprising finding. |
| **fig_breach_round_hist.png** | Distribution of *which round* the breach happens, per model. gpt-3.5 falls at rounds 1–2; gpt-4o-mini only cracks under sustained pressure. | **"How fast do they break" slide** — motivates multi-turn testing. |
| **fig_heatmap_model_vector.png** | ASR heatmap, model × attack vector, two panels (confidentiality / integrity), value in every cell. | **The "attack surface" slide** — dense, rigorous, one figure covers everything. |
| **fig_asr_by_vector.png** | Grouped bars: ASR per attack vector per model. Authority/Cipher/Many-shot devastate gpt-3.5; gpt-4o-mini's only chink is Roleplay. | "Which attacks work" slide / appendix. |
| **fig_asr_by_scenario.png** | Grouped bars: ASR by boundary (confidentiality vs integrity) per model. | Appendix. |
| **fig_km_facet_conf.png** | KM curves faceted by the 4 attack vectors, confidentiality boundary. | Deep-dive / appendix on confidentiality. |
| **fig_km_facet_integ.png** | Same, integrity (tool-firing) boundary. | Deep-dive / appendix on integrity. |

### Log-rank tests (pre-registered pairs, matched scenario × vector)

| Pair | Scenario · Vector | χ² | p | Result |
|---|---|---|---|---|
| gpt-4o-mini vs gpt-3.5-turbo | conf · CIPHER | 38.8 | 4.8e-10 | **highly significant** separation |
| gpt-5-nano vs gpt-3.5-turbo | conf · MANY_SHOT | 18.1 | 2.1e-05 | **highly significant** separation |
| (3 more pairs) | involve o4-mini / gpt-4-turbo | — | — | not computable — those models weren't collected (shared OpenAI key ran out) |

Both computable pre-registered comparisons confirm the weak model is significantly more breakable. Report honestly that 3 pairs referenced models we couldn't finish.

---

## SECONDARY figures (LLM Judge — qualitative degradation, advisory only)

> The Judge (Gemini, isolated + brand-blind + canary-free) scores only persona/refusal
> degradation. It **never** defines a breach — the primary metrics above are 100%
> deterministic. Present these as a *secondary, qualitative* corroboration. **(These
> regenerate as the judge pass fills in — check the `n=` on each figure before using; the
> ranking is already stable.)**

| File | What it shows | Best for |
|---|---|---|
| **fig_judge_verdict_by_model.png** | Stacked bar: share of replies judged No-degradation / Weak-refusal / Persona-break, per model. gpt-3.5 ~64% persona-break vs ~31% for the others. | The "qualitative degradation" slide. |
| **fig_judge_degradation_by_model.png** | Mean degradation score (0–1) per model with error bars — mirrors the ASR ranking from an independent signal. | The clean "second signal agrees" slide. |
| **fig_judge_vs_deterministic.png** | **What the Judge adds vs the code detector.** On rounds the detector flags a breach, the Judge agrees ~95%; on no-breach rounds it still flags ~37% "soft" degradation the code can't see. | The "why we have TWO signals" slide — explains the Judge's purpose. |
| **fig_judge_breach_concordance.png** | Mean degradation on breach vs non-breach rounds — the Judge independently "sees" the collapse the detector flags (concordance, not causation). | Alternative to the one above; "our two signals agree." |
| **fig_judge_verdict_by_scenario.png** | Verdicts split by boundary type. | Appendix. |

---

## Also available (tables + raw numbers)

- `../analysis_final/REPORT.md` — full per-cell ASR table with CIs, N, censoring.
- `../analysis_final/asr_table.csv`, `survival_curves.csv`, `logrank.csv` — raw numbers for custom charts.
- `../judge_scores.csv` — per-round Judge verdicts (transcript_ref keyed) for the secondary analysis.

## Regenerate

```
./.venv/bin/python scripts/make_figures_plotly.py      # the whole gallery (primary + secondary), Plotly
```

*(The earlier matplotlib scripts `scripts/make_figures.py` and `scripts/make_judge_figures.py`
are superseded by `make_figures_plotly.py`, which is the current, consistent generator.)*
