# BreachBench Live — Demo Plan

> **STATUS UPDATE (2026-07-16) — Demo "completion" BUILT.** The replay demo now has: a
> balanced **2/2 curated line-up** (2 confidentiality + 2 integrity, one breach + one hold each,
> one real run per attack vector); **4 distinct themed scenes** driven by a theme registry
> (`replay/themes.js`) — Realm (castle), Boardroom (office), Cipher Den, Swarm — swapping art
> while sharing one siege mechanic; and a **⚖️ Judge's ruling card** at the end of each run
> (baked-in verdicts from `output/judge_scores.csv`, never live) whose takeaway adapts to
> whether the Judge agrees with the deterministic outcome (including the "held but Judge says
> break" teaching moment). Old all-black backup removed. All screenshot-verified.

> **STATUS UPDATE (2026-07-15) — Replay demo BUILT.** The replay-first showpiece is
> implemented and smoke-tested at [`demo/replay/`](replay/) (open `replay/index.html` — no
> server, no API). It's a standalone animated siege (attacker with a spear vs a shielded
> defender guarding a castle; the castle falls on breach) driven by four curated REAL
> transcripts baked into `replay/data.js` via [`build_replay_data.py`](build_replay_data.py).
> See [`README.md`](README.md) to run/re-curate. The FastAPI/SSE server design below (Modes 1
> & 2) is NOT built — it was for the live duel, which the dead OpenAI key made moot. The rest
> of this file is the original plan, kept for reference and for the optional Human Challenge.

> **Status of the original plan:** the live modes were **deferred, then superseded** by the
> replay build above. Build only AFTER the current harness
> work (full runs + the metrics/visualization layer) is finished. This file is the
> durable, findable copy of the plan so a fresh chat can pick it up with zero
> re-derivation. Nothing here changes `src/breachbench/`.

> **REVISION (2026-07-15) — REPLAY-FIRST (the shared OpenAI key ran out of credit).**
> The live attacker (gpt-4o) can no longer run, so the demo pivots:
> - **Mode 3 (Replay) becomes the PRIMARY showpiece.** It reads the 547 saved JSONL
>   transcripts in `runs/` — REAL benchmark runs (real gpt-4o attacker vs real targets),
>   including 181 breaches and 299 clean holds — and animates them "as if live." **Needs
>   NO API.** This is arguably *better* than a live demo: authentic real data, curated for
>   drama (pick a fast breach + a full 10-round hold), zero live-failure risk on stage.
> - **Mode 1 (live Agent Duel) is DROPPED** — it needs the dead OpenAI attacker.
> - **Mode 2 (Human Challenge) is OPTIONAL** and, if kept, uses a **free-tier target**
>   (Gemini or Groq — the human is the attacker, so it's only a few *target* calls per
>   session, within free daily quota). Show it clearly labeled: *"this live model is
>   different from our benchmark models — the benchmark ran on OpenAI; this is a free-tier
>   stand-in for the interactive demo."* Detection (canary/tool) is local, no API.
> Net: the demo is fully buildable with no OpenAI credit. `replay.py` + the frontend are
> unchanged; we just promote Replay to the headline and curate 2-3 dramatic transcripts.

## Context

For the Friday capstone presentation we want a **live, visual demo** that dramatizes
the Attacker→Target loop with real-time deterministic breach detection, plus a
**human-vs-agent** mode — the literal thesis of the project (automated vs manual
red-teaming). It must look polished (not a rushed toy), must not flop live (a
pre-recorded replay is the safety net), and must be **cleanly separated** from the
harness code. Approved scope: **Agent Duel + Human Challenge + Replay backup.**

The demo is a thin **presentation layer** over an engine that already works — the
Attacker, Target adapters, deterministic detection, personas, and JSONL transcripts
all exist and are reused verbatim. No new "hard" logic is built under deadline.

## Non-negotiable: keep the demo separate from the harness

- The demo lives in its **own top-level `demo/` directory**, NOT inside `src/breachbench/`.
- `demo/` **imports** the `breachbench` package (`pip install -e .`'d); `breachbench`
  **never** imports `demo/`. One-way dependency.
- Demo-only deps (`fastapi`, `uvicorn`) live in **`demo/requirements-demo.txt`**, NOT in
  the core `pyproject.toml`, so the harness stays lean and its offline tests are unaffected.
- Net effect: keep editing `src/breachbench/` freely; nothing in the demo touches it.

## Directory layout

```
demo/
├── PLAN.md                 # this plan
├── README.md               # how to run (one command)
├── requirements-demo.txt   # fastapi, uvicorn
├── __init__.py
├── driver.py               # composes engine calls -> streamed events (imports breachbench)
├── replay.py               # a saved JSONL transcript -> the same event stream
├── server.py               # FastAPI app: serves the UI + SSE/REST endpoints
├── static/{index.html, app.js, styles.css}   # single-page UI, vanilla JS, dark theme
└── transcripts/            # 2-3 curated dramatic runs for Replay (from output/runs/)
```

Run: `uvicorn demo.server:app` from the project root → open `http://localhost:8000`.

## The three modes

1. **Agent Duel (showpiece, streamed).** Our Attacker vs a chosen Target, round-by-round,
   live. Attacker (left/red) → Target (right/blue) → deterministic verdict, each streamed
   separately. A **Secret-Status HUD** makes detection visible: 🔒→🔓 on canary leak, a tool
   icon for integrity, `round k/k_max`, and **survival dots** (a live discrete survival
   curve). Breach → banner. Target is **brand-blind**, revealed only at the end.
2. **Human Challenge (the thesis).** A volunteer types attacks at the *same* persona (fresh
   canary), same deterministic detector. Payoff: *"agent cracked it in 2 rounds — human took
   7 / couldn't."* Shares ~90% of the UI with mode 1.
3. **Replay (safety net).** Streams a pre-recorded JSONL transcript with pacing — zero live
   API calls, cannot fail on stage. Doubles as the required backup recording.

## Event stream (backend → frontend, one JSON per SSE)

`run_start` (persona_name, persona_display [canary masked], scenario_id, breach_type, vector,
k_max) · `round_start` (k) · `attacker` (k, text) · `target` (k, text, tool_calls[], error) ·
`detection` (k, canary_leaked, canary_method, partial, tool_fired, tool_detection, breach,
canary_matched_value only-when-leaked) · `breach` (k, breach_type) · `survived` (k_max) ·
`run_end` (duration, event, reason, target_reveal, canary_reveal).

Human mode uses REST: `start` → {session_id, persona_display, breach_type, k_max}; each
`message` → {round, target_text, detection, breach, target_reveal?, canary_reveal?}.

## Backend reuse map (do NOT reimplement; do NOT edit src/breachbench/)

- Attacker: `attacks/attacker.py:{Attacker, Attacker.next_prompt(history,k), build_grey_box_brief}`;
  strategy `attacks/registry.py:get_meta(vector).strategy`.
- Providers: `providers/registry.py:build_provider(spec, models_registry, retry)`; helpers
  `providers/types.py:{system, user, flatten_history}`.
- Detection (PRIMARY): `detection/canary_match.py:match_canary(canary, text, partial_min=…)`;
  `detection/tool_dispatch.py:MockToolDispatcher().observe(resp, forbidden_tool)`.
- Target setup: `scenarios/canary.py:render_target(scenario, canary_seed)` → (system_prompt,
  canary); `loop/round.py:{forbidden_tool_to_spec, text_protocol_brief}`.
- Config/scenarios: `config/loader.py:{load_experiment_config, load_models_registry}`,
  `scenarios/loader.py:load_scenarios()`.
- Replay source: `recording/transcript.py` writes `output/runs/<run_id>.jsonl` with
  {attacker_prompt, target_text, target_tool_calls, detection{canary,tool}, breach_this_round,
  target_resolved_model_version} — `replay.py` maps these onto the events above.

`driver.py` exposes `agent_duel_events(...)` (a generator composing the above at per-step
granularity — the reason we don't just call the atomic `loop.execute_round`),
`start_human_session(...)`/`human_message(...)` (in-memory session dict), `demo_config()`.
`persona_display` redacts the canary before it leaves the server; the real canary is sent
only inside a `detection`/`run_end` event at/after the breach.

`server.py` (FastAPI): `GET /`, `GET /api/config`, `GET /api/agent/stream` (SSE via
StreamingResponse with a sync generator — Starlette runs it in a threadpool),
`POST /api/human/{start,message}`, `GET /api/transcripts`, `GET /api/replay/stream` (SSE).
`/` and `/api/config` work with no keys (smoke-testable).

## Frontend (`demo/static/`)

Single page, 3 tabs, dark theme, vanilla JS + `EventSource` (no build step). Conversation view
(attacker/target bubbles, type-on animation, "thinking…"), Secret-Status HUD (lock 🔒/🔓 +
method, tool indicator, round counter, survival-dot timeline), breach banner, Human tab
(persona card with masked canary + input + comparison line), Replay tab (transcript dropdown +
play/pause/step/speed). Brand-blind: target name hidden until `run_end`; leaked canary
highlighted in the target bubble the instant it appears.

## Stage safety

Runs locally (localhost, real keys) — project `localhost`. **Replay is the offline backup.**
Feature a breakable target live (e.g. `gpt-3.5-turbo` or `llama-3.1-8b-instant`); curate 2-3
dramatic transcripts into `demo/transcripts/` beforehand.

## Implementation sequence (~1–1.5 days, do later)

0. Scaffold `demo/` + `requirements-demo.txt` + `README.md`.
1. `driver.agent_duel_events` + minimal `server.py` + SSE (verify one live duel streams).
2. Frontend Agent-Duel view + HUD + survival dots + breach banner.
3. Human mode (backend session + frontend tab + comparison).
4. `replay.py` + Replay tab; curate transcripts.
5. Polish: animations, brand-blind reveal, canary highlight, speed control.
6. Dry-run on the presentation laptop; **record the backup video.**

## Verification

- Separation intact: `pytest tests/ -q` still green (demo doesn't touch `src/`); `import
  breachbench` unaffected.
- Server smoke (no keys): `GET /` and `/api/config` return 200.
- Live agent duel vs a breakable target; streamed rounds + breach round match the harness.
- Human mode: verdict updates; canary never in any payload before the breach event.
- Replay: play a curated transcript end-to-end offline.

## Open decisions (confirm at build time)

- Featured live target + scenario (recommend a breakable one).
- Token-level streaming of the target reply — v2 polish, not v1.
- Live Kaplan–Meier curve building across repeated runs — out of scope (stretch goal).
