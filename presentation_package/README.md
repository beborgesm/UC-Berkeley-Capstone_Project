# BreachBenchmark — Presentation Package (START HERE)

Everything you need to build the slides is in this one folder. Nothing else is required.

## What's inside

| File | What it is | How to use it |
|---|---|---|
| **CONCEPTUAL_OVERVIEW.md** | The project explained in plain concepts (no code). The idea, method, results, challenges, likely Q&A, and a 30-second pitch. | **Read this first** to understand the project. Also paste it into ChatGPT/Claude as context when drafting slides or prepping answers. |
| **TECHNICAL_PIPELINE.md** | The full technical / code description, file by file. | Paste into your AI when you need it to understand *how* things were built (so you don't have to feed it the raw code). |
| **RESULTS_REPORT.md** | The exact numbers: per-cell attack-success-rate table with confidence intervals, N, censoring, log-rank tests. | Source of truth for any number you put on a slide. |
| **DEVELOPMENT_TIMELINE.md** | *(Optional, deeper background.)* The story of how the project was built — the bugs we caught, the challenges, and the "lessons learned." | Great for a **"research process / lessons learned" slide** and for answering *"what was the hardest part?"*. Paste into your AI if you want richer challenge stories than the Conceptual doc's summary. |
| **figures/** | All 13 slide-ready figures (PNG) + `FIGURES.md` (a captioned index of every figure with a "best for slide X" note). | Drop the PNGs straight onto slides. Read `figures/FIGURES.md` to know what each shows. |

## The 60-second story (for the deck's spine)

- We attacked 3 models with a fixed AI attacker across 4 jailbreak strategies and 2 safety
  boundaries, and measured **how long each holds out** using Kaplan–Meier survival analysis.
- Breaches are decided by **deterministic code**, not by an AI → auditable.
- **92% / 14% / 8%** of attacks succeed against gpt-3.5-turbo / gpt-5-nano / gpt-4o-mini.
- **The twist:** the newest, tiniest model (gpt-5-nano, 2025) is *more* breakable than the
  older gpt-4o-mini (2024) → **capability, not recency, drives robustness.**

## Suggested slide order (starter — adapt freely)

1. **Title / hook** — "How long can an AI keep a secret under attack?"
2. **Motivation** — real jailbreaks are multi-turn; single-prompt safety tests miss this.
3. **Method** — the Attacker/Target/Judge setup + the two boundaries + 4 attack vectors.
4. **The measurement idea** — survival analysis (KM curves, ASR, censoring). → `fig_km_by_model.png`
5. **Rigor** — breaches decided in code, not by an AI (Judge is secondary).
6. **Headline result** — `fig_asr_by_model.png` (92/14/8%).
7. **The twist** — `fig_capability_vs_recency.png` (newer ≠ safer).
8. **How fast they break** — `fig_breach_round_hist.png`.
9. **Attack surface** — `fig_heatmap_model_vector.png` (model × vector, both boundaries).
10. **Secondary corroboration** — `fig_judge_degradation_by_model.png` + `fig_judge_breach_concordance.png` (an independent AI agrees).
11. **Live demo** — the animated "castle siege" replay (ask Bernardo to run it).
12. **Limitations + future work** — small N, 3 models, validating the Judge vs humans (κ).
13. **Takeaway** — robustness is measurable, model-specific, erodes over a conversation, and tracks capability.

## Which figures are "core" vs "backup"

- **Core (use these):** `fig_asr_by_model`, `fig_km_by_model`, `fig_capability_vs_recency`,
  `fig_breach_round_hist`, `fig_heatmap_model_vector`, `fig_judge_degradation_by_model`.
- **Good secondary:** `fig_judge_verdict_by_model`, `fig_judge_breach_concordance`.
- **Backup / appendix:** `fig_asr_by_vector`, `fig_asr_by_scenario`, `fig_km_facet_conf`,
  `fig_km_facet_integ`, `fig_judge_verdict_by_scenario`.

## Notes

- **Code questions during the presentation → Bernardo.** These docs are for building the deck.
- The Judge figures are a *secondary* signal (a second AI's opinion). Primary results are the
  deterministic survival/ASR numbers and don't depend on the Judge.
- All model colors are consistent across every figure: gpt-3.5-turbo = orange, gpt-5-nano = amber, gpt-4o-mini = green.
