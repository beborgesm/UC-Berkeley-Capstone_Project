# Human gold set (future work — hook only)

This directory holds human labels used to assess the **secondary** LLM Judge's
reliability (Cohen's / Fleiss κ). It is **not** used for any primary breach metric —
those are deterministic (`detection/`). The reliability computation is currently a
stub (`analysis/reliability.py`); this README fixes the data format so the hook is
ready.

## Format

One CSV per labeling batch, one row per human-labeled round:

```csv
transcript_ref,human_verdict
<run_id>#<round_index>,NO_DEGRADATION
<run_id>#<round_index>,PERSONA_BREAK
<run_id>#<round_index>,WEAK_REFUSAL
```

- `transcript_ref` joins to `rounds.csv` (`transcript_ref` column) and to the JSONL
  transcript store (`runs/<run_id>.jsonl`), so a labeler can read the exact target
  output that was judged.
- `human_verdict` must be one of the `JudgeVerdict` enum values:
  `NO_DEGRADATION | PERSONA_BREAK | WEAK_REFUSAL`.

## Procedure (when implemented)

1. Sample rounds (stratified by cell) from `rounds.csv`.
2. Present each round's target output to human raters **brand-blind** and without
   the canary — mirroring the Judge's isolation.
3. Join `human_verdict` to the Judge's `judge_verdict` on `transcript_ref`.
4. Compute Cohen's κ (single judge) or Fleiss κ (panel) via
   `analysis/reliability.py`.

Report κ alongside every degradation figure; the deterministic breach metrics never
depend on it.
