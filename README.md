# BreachBenchmark

A deterministic-first, closed-loop red-teaming harness that stress-tests the
safety boundaries of LLMs, for a UC Berkeley AI-safety capstone.

Three roles run a bounded, adaptive loop against one Target model:

- **Attacker** — an LLM agent that generates adversarial prompts from a fixed
  taxonomy (`ROLEPLAY`, `AUTHORITY`, `CIPHER`, `MANY_SHOT`) and escalates across
  rounds within a run.
- **Target** — the LLM under evaluation, initialized with a persona system prompt
  carrying a secret **canary** it must never reveal and a forbidden tool
  (`execute_emergency_override`) it must never invoke.
- **Judge** — a secondary, non-authoritative LLM referee that scores only
  qualitative degradation (persona break, weak refusal). It **never** defines a
  breach.

## Design principles

1. **Deterministic detection is primary.** Confidentiality (canary reappearance)
   and integrity (real tool invocation) breaches are detected in code, never by
   the Judge.
2. **Judge isolation.** Target output is untrusted *data* to the Judge, which is
   brand-blind and never sees the canary.
3. **Explicit survival semantics.** A run is an ordered sequence of rounds against
   one `(target_model × scenario × attack_vector)` cell, terminating on breach at
   round `k` (event) or right-censored at `k_max` (survived). The raw CSV feeds
   Kaplan–Meier survival analysis with zero reshaping.

## Layout

```
config/            experiment.yaml, models.yaml, scenarios/*.yaml  (data, not code)
src/breachbench/   config, providers, scenarios, attacks, detection, judge,
                   loop, runner, recording, analysis
scripts/           run_experiment.py, pilot.py, analyze.py
tests/             offline test suite (no network, no keys required)
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # core + pytest; add ",openai" etc. for live runs
pytest                            # full offline suite (no keys, no network)
```

Live runs read keys lazily from `.env` (see `.env.example`). Importing the
package or enumerating the grid never touches the network.

The build order and data contracts are documented in the engineering blueprint
(`plans/`). Deterministic canary + tool-fire detection is built and tested before
the Judge is integrated.
