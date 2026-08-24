# Published dataset

Every file here was produced by live runs against endpoints that no longer answer to us (the
shared OpenAI account's credit is exhausted). **It cannot be regenerated.** Treat it as
read-only: the analysis, the figures and the demo all read from it, and nothing in the
pipeline writes back to it.

A live run writes to `output/` and `runs/` instead — both gitignored — so re-running the
harness can never overwrite what's here.

Integrity is machine-checked:

```bash
python scripts/verify_dataset.py     # or: make verify
```

---

## Files

| File | Rows | What it is |
|---|---|---|
| `rounds_benchmark.csv` | 3,424 rounds · 480 runs | **The benchmark.** One row per attack round, for the 3 fully-collected models. This is what every headline number, figure and log-rank test is computed from. |
| `rounds_raw.csv` | 3,843 rounds · 523 runs | Everything the harness ever recorded, including the partially-collected 4th model (`gpt-4-turbo`). Superset of the above. |
| `judge_scores.csv` | 960 rounds | **Secondary**, non-authoritative LLM-Judge verdicts (persona/refusal degradation only). A balanced ~28% sample, not a census. Never used for a breach decision. |
| `ledger.jsonl` | 523 lines | The runner's append-only record of completed runs — what made the multi-day collection resumable and power-off-safe. |
| `transcripts/*.jsonl` | 547 files | The full conversation for every run: each attacker prompt, each target reply, the tool calls, and the detection result per round. |

Column-by-column definitions: [`docs/DATA_DICTIONARY.md`](../docs/DATA_DICTIONARY.md).

## The benchmark grid

3 targets × 2 boundaries × 4 attack vectors × 20 repetitions = **24 cells, 480 runs**, each
run up to `k_max = 10` rounds. Attacker is a single fixed instrument (`openai:gpt-4o`) and is
*not* a grid axis.

| | |
|---|---|
| **Targets** | `gpt-3.5-turbo` (2023) · `gpt-4o-mini` (2024) · `gpt-5-nano` (2025) |
| **Boundaries** | `conf_vault_v1` (a canary token that must not be revealed) · `integ_override_v1` (a forbidden tool that must not be invoked) |
| **Vectors** | `ROLEPLAY` · `AUTHORITY` · `CIPHER` · `MANY_SHOT` |
| **Outcomes** | 181 breaches (events) · 299 held to `k_max` (right-censored) · **0 administratively censored** |

`rounds_benchmark.csv` is *derived*, not hand-made — regenerate it any time with:

```bash
python scripts/make_benchmark_subset.py   # rounds_raw.csv + the roster in config/experiment.yaml
```

## Why `rounds_raw.csv` has a 4th model

The declared roster was five targets. The shared OpenAI account hit its billing wall
mid-collection, which also killed the fixed `gpt-4o` attacker, so no further live runs of any
kind were possible: `gpt-4-turbo` finished 43 of 160 runs (2 of its 8 cells at full N) and
`o4-mini` was never started.

That partial data is published rather than deleted, and analysed separately in
[`results/analysis_extended/`](../results/analysis_extended/) — it is kept out of the headline
because promoting 2 complete cells of a 2/8-complete model into a table of fully-balanced
models would misrepresent the grid. The full dated account is in
[`docs/PREREGISTRATION.md`](../docs/PREREGISTRATION.md).

## The 24 transcripts with no CSV row

`transcripts/` holds 547 files but `rounds_raw.csv` has 523 runs. The extra 24 —
`8f8230fc1b192931-0003…0019` and `d34e81ad052c6377-0000…0006`, both `gpt-4-turbo`
confidentiality cells — are **not missing data**. They are the runs that were in flight when
the billing wall hit; every one ends in a `429 insufficient_quota`.

A rate-limit is a *transient* failure, so the harness's operational rule **invalidated and
rescheduled** them instead of recording them as "survived one round, then censored". The
reschedule never happened, because the key stayed dead — so the transcripts exist and the
survival rows correctly do not.

They ship deliberately: they are the audit trail showing the harness discarded an
infrastructure failure rather than laundering it into a data point. That rule was itself an
amendment, made after throttling polluted an earlier collection — see
[`docs/PREREGISTRATION.md`](../docs/PREREGISTRATION.md) §3B and
[`DEVELOPMENT_TIMELINE.md`](../DEVELOPMENT_TIMELINE.md) Phase 6.

`scripts/verify_dataset.py` asserts this list exactly, so an *undocumented* orphan fails the check.

## Not published here

The earlier **temperature-0.7 generation** (320 runs, 2 models) is retained offline and was
never mixed into this dataset. Its result — that 0.7 and 1.0 agree — is reported in
[`docs/TEMPERATURE_ABLATION.md`](../docs/TEMPERATURE_ABLATION.md).

## Ethics note

The "secret" in every confidentiality run is a freshly generated random token with no meaning
outside the run, and the "dangerous" tool is a mock that does nothing. No real credential was
ever used, elicited or stored, and no real action was ever triggered. The personas make the
*situation* realistic; the payload is deliberately inert. See
[`docs/realistic_personas.md`](../docs/realistic_personas.md).
