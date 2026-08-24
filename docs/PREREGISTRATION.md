# Pre-registration record

> **What this file is.** The between-model log-rank comparisons in this project are
> *pre-registered*: they were committed to `config/experiment.yaml` **before any of the
> analysed data existed**, so they cannot be cherry-picked after the fact. This document is
> the frozen record of that declaration — the original roster and all five hypothesis pairs,
> verbatim — together with the dated disposition of every item, including the ones that were
> never collected.
>
> **Nothing here was re-declared after outcomes were inspected.** Items that could not be
> computed are marked as such; none were quietly replaced with something that worked.

- **Locked:** 2026-07-15
- **Locked before:** the temperature-1.0 data collection began (the analysed dataset)
- **Live config:** [`config/experiment.yaml`](../config/experiment.yaml) — carries the
  *collected* subset, and points back here
- **Results:** [`results/analysis/REPORT.md`](../results/analysis/REPORT.md) (benchmark) and
  [`results/analysis_extended/REPORT.md`](../results/analysis_extended/REPORT.md) (appendix)

---

## 1. Declared target roster

Ordered fast → slow, so the quick models finished first overnight and the slow reasoning
model ran last (the runner is resumable, so a partial finish was recoverable).

| # | Target | Rationale at declaration time | Collected? |
|---|---|---|---|
| 1 | `openai:gpt-3.5-turbo` | 2023 — weak, the "punching bag" that supplies breach events | ✅ **complete** — 160 runs, 8/8 cells |
| 2 | `openai:gpt-4o-mini` | 2024 efficient — mid-robust | ✅ **complete** — 160 runs, 8/8 cells |
| 3 | `openai:gpt-5-nano` | 2025 small — mid / generational bridge | ✅ **complete** — 160 runs, 8/8 cells |
| 4 | `openai:gpt-4-turbo` | 2023 flagship — mid-robust | ⚠️ **partial** — 43 runs, 2/8 cells complete |
| 5 | `openai:o4-mini` | reasoning — expected most robust | ❌ **not started** — 0 runs |

**Why 4 and 5 are incomplete.** The shared OpenAI account ran out of credit during
collection. That was a billing wall, not a rate limit, and it took down the fixed `gpt-4o`
**attacker** as well as the remaining targets — so no further live runs of *any* kind were
possible, on any model, and topping up the grid later was not an option. See
[`DEVELOPMENT_TIMELINE.md`](../DEVELOPMENT_TIMELINE.md) Phase 7.

Both entries are retained as commented roadmap lines in `config/experiment.yaml`. Because
cell identity derives from the target spec, restoring a key and uncommenting a line resumes
straight into the same resumable output — no re-run of the collected 480.

**What was published anyway.** The partial `gpt-4-turbo` data was *not* discarded. All 523
runs (4 models) ship as `data/rounds_raw.csv` and are analysed in
`results/analysis_extended/`; the headline benchmark is the clean, fully-balanced 3-model
subset (`data/rounds_benchmark.csv`, 480 runs, 24 cells).

---

## 2. Declared log-rank pairs (all five, verbatim)

Declared in `config/experiment.yaml` on 2026-07-15, matched on (scenario, vector):

```yaml
logrank_pairs:
  # H1 (generational safety-tax): newer small model resists cipher-extraction better than the older.
  - scenario_id: conf_vault_v1
    attack_vector: CIPHER
    model_a: { vendor: openai, model_version: gpt-4o-mini }
    model_b: { vendor: openai, model_version: gpt-3.5-turbo }
  # H2 (newest-small vs old-weak): gpt-5-nano more robust than gpt-3.5-turbo.
  - scenario_id: conf_vault_v1
    attack_vector: MANY_SHOT
    model_a: { vendor: openai, model_version: gpt-5-nano }
    model_b: { vendor: openai, model_version: gpt-3.5-turbo }
  # H3 (reasoning vs standard, integrity): the reasoning model resists authority-framed tool misuse better.
  - scenario_id: integ_override_v1
    attack_vector: AUTHORITY
    model_a: { vendor: openai, model_version: o4-mini }
    model_b: { vendor: openai, model_version: gpt-4o-mini }
  # H4 (old flagship vs new small): gpt-4-turbo vs gpt-4o-mini — comparable robustness?
  - scenario_id: conf_vault_v1
    attack_vector: ROLEPLAY
    model_a: { vendor: openai, model_version: gpt-4-turbo }
    model_b: { vendor: openai, model_version: gpt-4o-mini }
  # H5 (most-robust vs weakest): sanity/power check — strong separation expected.
  - scenario_id: conf_vault_v1
    attack_vector: CIPHER
    model_a: { vendor: openai, model_version: o4-mini }
    model_b: { vendor: openai, model_version: gpt-3.5-turbo }
```

### Disposition

| ID | Hypothesis | Cell | Status | Result |
|---|---|---|---|---|
| **H1** | Generational safety-tax: `gpt-4o-mini` resists cipher-extraction better than `gpt-3.5-turbo` | conf · CIPHER | ✅ **computed** | χ² = 38.78, **p = 4.8 × 10⁻¹⁰**, n = 20/20 — supported |
| **H2** | Newest-small vs old-weak: `gpt-5-nano` more robust than `gpt-3.5-turbo` | conf · MANY_SHOT | ✅ **computed** | χ² = 18.09, **p = 2.1 × 10⁻⁵**, n = 20/20 — supported |
| **H3** | Reasoning vs standard on integrity: `o4-mini` resists authority-framed tool misuse better than `gpt-4o-mini` | integ · AUTHORITY | ❌ **not computable** | `o4-mini` never collected (credit exhaustion, 2026-07) |
| **H4** | Old flagship vs new small: `gpt-4-turbo` vs `gpt-4o-mini` — comparable robustness? | conf · ROLEPLAY | ⚠️ **computable on partial data** | χ² = 2.39, **p = 0.12**, n = 20/20 — no detected difference; reported in `results/analysis_extended/`, *not* in the headline benchmark, because `gpt-4-turbo`'s other 6 cells are missing |
| **H5** | Sanity/power check: `o4-mini` vs `gpt-3.5-turbo` — strong separation expected | conf · CIPHER | ❌ **not computable** | `o4-mini` never collected (credit exhaustion, 2026-07) |

**Read H4 carefully.** Its cell happens to be one of the two `gpt-4-turbo` cells that *did*
finish at full N=20, so the test is validly powered for that comparison. It is kept out of the
headline report only because promoting a single cell of a 2/8-complete model into a table of
fully-balanced models would misrepresent the grid. Non-significance here is **not** evidence
of equivalence — at N=20 the test is underpowered for small differences, which is exactly why
the report carries an `underpowered` flag.

**Multiplicity.** Five pairs were declared; two were computed. No correction was applied,
and none is claimed — both computed results clear any conventional correction at these
p-values by several orders of magnitude, and the report states N and censoring for every cell
so a reader can apply their own.

---

## 3. Protocol amendments (dated)

Two amendments were made to the protocol after locking. Both are recorded here so the audit
trail sits in one place, and both were driven by *operational* or *data-quality* observations,
never by survival outcomes.

### A. Temperature standardised 0.7 → 1.0 (2026-07-15, before the analysed collection)

**What changed.** Target and attacker temperature moved from 0.7 to 1.0.

**Why.** The roster was extended to include GPT-5 / o-series models, whose endpoints accept
only the default temperature (1.0). A benchmark axis has to be constant across the roster, so
either every model ran at 1.0 or the newer models were excluded.

**Evidence it was safe.** The complete 320-run temperature-0.7 generation was re-run at 1.0
and the two agree — `gpt-3.5-turbo` breached identically (147/160 at both settings) and
`gpt-4o-mini` moved 7 → 12 breaches out of 160, within sampling noise. Numbers and method:
[`TEMPERATURE_ABLATION.md`](TEMPERATURE_ABLATION.md).

**Effect on results.** None — all published analysis is the temperature-1.0 generation. The
0.7 generation is retained offline and was never mixed into the published dataset.

### B. Transient operational failures invalidate rather than censor (2026-07-14)

**What changed.** The original threat model administratively censored *any* mid-run
operational failure that occurred after at least one valid round. The amended rule: a
**transient** failure (`RATE_LIMIT` / `CONNECTION` / `TIMEOUT`, enumerated in
`loop/run.py:_TRANSIENT_ERRORS`) **invalidates the run and reschedules it** — it is never
recorded. Only **non-transient** failures after a valid round still admin-censor.

**Why.** Under systematic free-tier throttling, 57% of Groq runs were being recorded as
"survived one round, then censored" — which is the *infrastructure* failing, not the model
holding. Left as-is, that would have injected dozens of fake early-censoring points into the
survival curves. The trigger was a data-*quality* check on the raw CSV, not an inspection of
outcomes. Rate-limit backoff was also made patient (honours `Retry-After`, up to 90 s over 8
attempts) so most runs complete rather than fail.

**Effect on results.** The tainted Groq/Gemini data was deleted and those vendors were
dropped as targets; the published OpenAI dataset was collected entirely under the amended
rule and contains **zero** `ADMIN_CENSORED_ERROR` runs (machine-checked by
`scripts/verify_dataset.py` and stated in every `REPORT.md` header). Full story:
[`DEVELOPMENT_TIMELINE.md`](../DEVELOPMENT_TIMELINE.md) Phase 6.

---

## 4. What was *not* pre-registered

Stated explicitly so the boundary is unambiguous:

- **Descriptive metrics** — per-cell ASR@k_max, Kaplan–Meier curves, bootstrap CIs and the
  ASR heatmaps are computed for *every* cell in the grid. They are descriptive, not
  hypothesis tests, and need no pre-registration.
- **The "capability, not recency" observation** — that the 2025 `gpt-5-nano` is more breakable
  than the 2024 `gpt-4o-mini` is a **post-hoc observation** from the descriptive ASRs, not a
  pre-registered test. It is reported as an observation, and H2 (which *was* pre-registered)
  tests something different: nano vs the 2023 model.
- **The secondary LLM Judge** — the entire degradation analysis is exploratory and
  non-authoritative by design. It can never define a breach, so it has nothing to
  pre-register. See [`LIMITATIONS.md`](LIMITATIONS.md).
