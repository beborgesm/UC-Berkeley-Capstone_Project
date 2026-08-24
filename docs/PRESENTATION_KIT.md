# Presentation kit — everything needed to build the deck

This is the "start here" page for anyone assembling slides or prepping to present, including
someone who has never written code but understands AI and maths. It points at the real
documents rather than duplicating them, so nothing here can drift out of date.

*(Code questions during the presentation → Bernardo.)*

## What to read, in what order

| Document | What it is | How to use it |
|---|---|---|
| [`CONCEPTUAL_OVERVIEW.md`](CONCEPTUAL_OVERVIEW.md) | The project in plain concepts — no code. Idea, method, results, challenges, likely Q&A, and a 30-second pitch. | **Read this first.** Also paste it into an AI assistant as context when drafting slides or rehearsing answers. |
| [`../results/analysis/REPORT.md`](../results/analysis/REPORT.md) | The exact numbers: per-cell attack-success rate with CIs, N, censoring, log-rank tests. | **Source of truth for any number on a slide.** |
| [`../results/figures/FIGURES.md`](../results/figures/FIGURES.md) | Captioned index of all 14 slide-ready PNGs, with a "best for slide X" note on each. | Read this, then drop the PNGs straight onto slides. |
| [`TECHNICAL_PIPELINE.md`](TECHNICAL_PIPELINE.md) | The full technical description, file by file. | Paste into an AI when it needs to understand *how* things were built, instead of feeding it raw code. |
| [`../DEVELOPMENT_TIMELINE.md`](../DEVELOPMENT_TIMELINE.md) | The story of the build — bugs caught, dead ends, lessons. | The **"research process / lessons learned"** slide, and the honest answer to *"what was the hardest part?"* |
| [`LIMITATIONS.md`](LIMITATIONS.md) · [`PREREGISTRATION.md`](PREREGISTRATION.md) | What the results don't establish; the locked hypotheses and their disposition. | The limitations slide, and the answer to any "isn't that cherry-picked?" question. |

## The 60-second story (the deck's spine)

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
5. **Rigor** — breaches decided in code, not by an AI (the Judge is secondary).
6. **Headline result** — `fig_asr_by_model.png` (92/14/8%).
7. **The twist** — `fig_capability_vs_recency.png` (newer ≠ safer).
8. **How fast they break** — `fig_breach_round_hist.png`.
9. **Attack surface** — `fig_heatmap_model_vector.png` (model × vector, both boundaries).
10. **Secondary corroboration** — `fig_judge_degradation_by_model.png` + `fig_judge_breach_concordance.png` (an independent AI agrees).
11. **Live demo** — the animated siege replay ([`../demo/`](../demo/)).
12. **Limitations + future work** — small N, 3 models, validating the Judge vs humans (κ).
13. **Takeaway** — robustness is measurable, model-specific, erodes over a conversation, and tracks capability.

## Core vs backup figures

- **Core (use these):** `fig_asr_by_model`, `fig_km_by_model`, `fig_capability_vs_recency`,
  `fig_breach_round_hist`, `fig_heatmap_model_vector`, `fig_judge_degradation_by_model`.
- **Good secondary:** `fig_judge_verdict_by_model`, `fig_judge_breach_concordance`.
- **Backup / appendix:** `fig_asr_by_vector`, `fig_asr_by_scenario`, `fig_km_facet_conf`,
  `fig_km_facet_integ`, `fig_judge_verdict_by_scenario`.

All figures share one palette, in every panel:
**gpt-3.5-turbo = orange · gpt-5-nano = amber · gpt-4o-mini = green.**

## Notes for the presenter

- The Judge figures are a *secondary* signal (a second AI's opinion). The primary results are
  the deterministic survival/ASR numbers and don't depend on the Judge at all — say this
  before showing them, and the obvious "isn't AI judging AI circular?" question answers itself.
- If asked why only 3 of 5 declared models: the shared API account ran out of credit
  mid-collection, which killed the attacker too. The partial 4th model is published in
  [`../results/analysis_extended/`](../results/analysis_extended/) and every pre-registered
  hypothesis is reported with its disposition. Nothing was dropped for being inconvenient.
- The demo is a **replay of real saved runs** — no API, no network, so it cannot fail live.
  Every word on screen is genuine benchmark data.
