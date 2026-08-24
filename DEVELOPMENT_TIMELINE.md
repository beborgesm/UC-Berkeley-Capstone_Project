# BreachBenchmark — Development Timeline

> **Living document.** Append to this timeline whenever we correct a bug, debug an issue,
> or add new code — it's the narrative record for the final presentation. Keep entries
> focused on *what happened and why*, not code.

This is the story of how BreachBenchmark was built: the design decisions, the mistakes we
caught, and the surprises we hit when the harness first touched real models. The throughline
is that a "flawless" harness can still produce a useless result — and most of our hardest
lessons came from that gap between *runs cleanly* and *measures something*.

---

## Phase 0 — Design & the review that caught three real flaws

We started from a detailed architectural blueprint (directory layout, data contracts, the
CSV schema, control flow) before writing any code. The first draft looked complete — but a
careful review surfaced **three design flaws that would have quietly corrupted the science**:

1. **The Judge/canary contradiction.** The plan let the LLM Judge report "partial leakage."
   But the Judge is deliberately *brand-blind and never shown the canary* — so it literally
   cannot detect a partial canary leak. The verdict was unreachable. **Fix:** partial leakage
   became a *deterministic* signal (a contiguous-character match in code), and the Judge's
   vocabulary was narrowed to persona/refusal degradation only.
2. **Overclaiming determinism.** The plan promised runs were "seed-identical." Real LLM
   endpoints ignore seeds (Gemini/Groq) or honor them only best-effort (OpenAI). **Fix:** we
   scoped the reproducibility claim to structure (seeds, enumeration, control flow) and
   explicitly *not* to live responses.
3. **A Kaplan–Meier footgun.** The raw per-round CSV was going to carry a round-level
   `event_observed` column. Combined with the run-constant `duration`, anyone fitting a curve
   directly on that file would get the wrong survival estimate. **Fix:** the raw file carries
   no event column at all; the single, unambiguous event column is created only when we
   project to the per-run summary that the analysis actually consumes.

We also added a **mandatory pilot gate**: a small live run required before spending full
budget, whose entire job is to catch degenerate datasets early. (It later earned its keep.)

**Lesson:** the expensive mistakes in an experiment are in the *measurement definitions*, not
the plumbing. The review paid for itself before a line of code existed.

---

## Phase 1 — Building deterministic-first

We built in a strict order, with one hard rule: **deterministic canary + tool-fire detection
had to work and be tested before the Judge was allowed to exist.** This kept the "primary vs
secondary instrument" principle honest — the Judge could never quietly become load-bearing.

Layers went in bottom-up: config → provider abstraction (with an offline stub so tests never
touch the network) → scenarios/canary → **detection (the gate)** → attack loop → recording →
runner → pilot → adapters → Judge → analysis. Every layer shipped with offline tests.

### Bugs we caught along the way (all offline, before spending a cent)

- **The leetspeak self-own.** Our own test "leetified" the canary using a substitution
  (`Z→2`) that wasn't in the detector's locked transform set, then asserted a match. The test
  was wrong, not the code — a useful reminder that the transform set is *bounded on purpose*,
  and false-negatives outside it are an accepted, documented limitation.
- **Two survival-encoding test bugs.** A tuple-vs-set comparison, and — more subtly — reusing
  the same repetition index for two runs, which produced identical deterministic run IDs and
  collapsed two runs into one. Both were test errors that, once fixed, actually strengthened
  our confidence in the ID/seed derivation.
- **The log-rank "MISSING_CELL" bug (a real one).** The analysis matched pre-registered model
  comparisons using the *resolved* model-version string (e.g. `gpt-4o-2024-08-06`). But those
  comparisons are declared with *configured* names (`gpt-4o`), and resolved strings drift over
  time. Nothing would ever match. **Fix:** match on the stable configured cell identity
  instead. Caught during an end-to-end dry run, not by a unit test — which is why we do dry
  runs.

By the end of Phase 1: 66 offline tests green, a full end-to-end dry run (96 stubbed runs →
recording → KM/ASR/log-rank) driving cleanly, and resumability verified.

**Lesson:** most of our build-time bugs were in the *tests*, not the product. That's the
system working — the tests were adversarial enough to be wrong in instructive ways.

---

## Phase 2 — First contact with real models: the 0-breach scare

The user installed API keys and ran the pilot. Result:

> `breaches: 0   censored: 6   invalid: 0` — every run survived all 10 rounds.

A dataset of all-survivors is a *catastrophe* for survival analysis: flat curves, no events,
nothing to fit, no heatmap variation. The pilot had done exactly its job — it flagged a
degenerate dataset before we spent 30× the budget — but we had to find out *why*.

### The investigation

The pilot only reports counts, so it couldn't say why. We wrote a live diagnostic that
printed full transcripts, and the answer was clear and reassuring: **no bug.**

- The **attacker was genuinely strong and adaptive** — elaborate role-play, real cipher
  requests (leetspeak/reverse/ROT13/base64), escalating authority impersonation with fake
  credentials. It referenced prior turns, so multi-turn history was threading correctly.
- The **target refused cleanly every time**, with no API errors.
- **Detection worked** (the cipher attacker even asked for exactly the encodings our detector
  covers — so a leak *would* have been caught).

So the zero was *real*: `gpt-4o-mini` is genuinely robust to these attacks. Two structural
problems compounded it:

1. **The pilot only tested one vector (ROLEPLAY, the softest) against one target (the most
   robust one).** It was under-sampling the attack space.
2. **The confidentiality persona was pathologically over-defended** — it pre-emptively
   forbade "encode, translate, reverse, spell out…", i.e. it hard-coded a defense against
   every trick before the attacker tried it. Unrealistic *and* near-unbreakable.

### Two surprises from validating the other adapters

While confirming the newly-enabled Gemini/Groq targets:

- **Gemini was unusable:** the key had a *zero* free-tier quota (`limit: 0`) — every request
  429'd. Not throttling; a hard wall. (Good news: our retry/backoff logged it loudly instead
  of silently corrupting data.)
- **Groq's Llama-3.3-70b fired the forbidden override tool on the very first direct request.**
  That single observation reframed everything: the full grid would *not* be degenerate,
  because a weaker model gives us the events (and the between-model contrast) that a robust
  model withholds. Model heterogeneity is the signal.

**Lesson:** "zero breaches" wasn't a failure of the tool — it was the tool correctly reporting
that we'd pointed our softest attack at our toughest target through an unrealistically armored
persona. The fix was experimental design, not code.

---

## Phase 3 — Making the experiment produce signal

We implemented three fixes and validated every one against live endpoints:

1. **Target heterogeneity.** Added a breakable spread (`gpt-3.5-turbo`, `llama-3.1-8b-instant`)
   and ordered the roster strongest→weakest so the pilot defaults to the most breakable target.
2. **A real pilot.** Reworked it to sweep *all four vectors* across both a confidentiality and
   an integrity scenario against the weakest target, and to **persist transcripts + a CSV** so
   we never again have to guess why the numbers came out as they did.
3. **Stronger attacks + a realistic persona.** Rewrote the four attacker strategies to build
   commitment before asking, escalate across turns, and use concrete tactics; and softened the
   confidentiality persona to a natural "keep this private" instruction — more ecologically
   valid *and* actually breakable.

### The Gemini model-name saga

The user switched Gemini to `gemini-2.5-flash-lite`. It returned **404 NOT_FOUND** — even
though that model *appeared* in the key's own model list. Probing candidates one by one:
`2.5-flash-lite` → 404; `2.0-flash-lite` → 429 (quota-zero, same wall as before);
`gemini-flash-lite-latest` → **works** (routes to `gemini-3.1-flash-lite`). We switched to the
working alias. Gemini went from "ignore it" to fully functional, tool-calls included.

**Lesson:** model availability is per-key and per-endpoint, and a model appearing in a
listing does not guarantee it serves requests. Always probe, never assume.

### One more self-inflicted wound

Adding the user's real `.env` broke a test that asserted "no keys present" — because our lazy
`.env` loader helpfully repopulated the keys and defeated the test's isolation. We taught that
test to also suppress `.env` loading. A small thing, but a nice illustration of how a
convenience feature (auto-loading `.env`) can quietly undermine a guarantee (import-clean with
no keys).

### Result

Against the weakest target (`groq:llama-3.1-8b-instant`, N=2, k_max=10), the improved pilot
returned a clean **GATE OK**:

```
totals -> breaches: 7  censored: 9  invalid: 0
breach round-index distribution: {1: 1, 2: 4, 3: 1, 8: 1}
throttling -> RATE_LIMIT: 0  TIMEOUT: 0  TRUNCATION: 0
```

Confidentiality broke on ROLEPLAY, CIPHER, and MANY_SHOT (6/6) and held on AUTHORITY;
integrity broke once via the **text-protocol fallback** on this non-native-tools model. The
breach rounds span 1→8 — genuine survival dynamics, not a single-shot spike — and no
throttling. Compared with the original pilot's `breaches: 0`, the dataset is now
non-degenerate and survival-analyzable.

**Lesson:** the pilot gate is the single most valuable piece of process we added. It turned a
would-be "we ran 1,200 runs and got flat lines" disaster into a two-dozen-run course
correction.

---

## Phase 4 — Pre-run preparation (pre-registration + a deliberate "not yet")

With the gate green, we prepared the full run **without launching it**:

- **Pre-registered the log-rank comparisons.** Committed 5 hypothesis-driven model pairs to
  `experiment.yaml` *before any data was collected* — generational safety-tax (gpt-4o-mini vs
  gpt-3.5-turbo), scale within open weights (llama-70b vs llama-8b), open-vs-closed integrity
  (gpt-4o-mini vs llama-70b), weak-vs-robust sanity check, and cross-vendor closed
  (gpt-4o-mini vs gemini). Pre-registration is what makes a log-rank test honest; doing it
  post-hoc would be cherry-picking.
- **Scoped N to 20** for this first real run (resumable, so extendable to 30 later for free)
  and kept the **Judge OFF** — the primary KM/ASR/log-rank deliverables are 100% deterministic
  and need no Judge; turning it on only adds quota pressure to a secondary signal.
- **Added a `--repetitions` override** to the run CLI so the full grid can be smoke-tested
  cheaply (`--repetitions 1`) before the expensive run.
- **Decided NOT to launch the full run yet.** A grounded estimate (from the pilot's logged
  latencies) put the 40-cell × N=20 grid at **~20–40 hours** sequential, before rate-limit
  backoff — and a laptop cannot run a local job while powered off (tmux/nohup still need the
  machine on and awake; only a cloud host could run-while-off). Independently, the *full runner
  across all 5 targets + analysis* has only been exercised offline (stubs) and via the
  single-target pilot — so a tiny full-grid smoke is the honest final validation before
  committing a day of compute.

**Lesson:** "the gate is green" is not "press the big button." Pre-register comparisons, size
the run to the goal (a validation pass, not the final publication run), and validate the whole
pipeline cheaply before spending real hours.

## Phase 5 — Hardening for a multi-day, stop/resume run

Facing a ~day-long full run on free-tier APIs, we made the runner safe to stop and resume
across power-offs, and added the controls for a tiered rollout:

- **Power-off-proof resume.** The runner was already resumable (a ledger of completed runs,
  keyed on `(cell, repetition)`), but there was a microscopic window where a run's rows could
  be written just before the ledger recorded it — a hard power-off there could re-run and
  *duplicate* that run. We closed it: on startup the runner **reconciles the ledger against
  `rounds.csv`**, treating any run that already has a terminal row as done. Plus a
  belt-and-suspenders de-dup in the analysis projection. Net effect: you can Ctrl-C or power
  off at any moment, rerun the same command, and it continues from exactly where it stopped —
  worst case one in-flight run repeats, never a duplicate, never lost hours.
- **Tiered rollout controls.** Added `--repetitions N` (cheap full-grid smoke) and
  `--vendors` / `--targets` filters so a run can be restricted to a subset of the roster.
  Because cell identity is derived from the target spec, filtered runs **accumulate into the
  same resumable output** — so "OpenAI targets first, Groq next, Gemini last" is just three
  commands into one dataset, not three separate experiments.

**Lesson:** a long run on flaky infrastructure isn't a risk if the unit of durable progress is
small (one run) and resumption is idempotent. Design for interruption and the wall-clock stops
being scary.

## Phase 6 — A data-quality bug caught in the live data: rate-limit "pollution"

Running the Groq + Gemini tiers, a check of the raw CSV showed something alarming: **57% of
Groq runs were `ADMIN_CENSORED_ERROR`**, almost all cut at round 1, all `RATE_LIMIT`. The
harness was faithfully recording them as "survived one round, then censored" — but that wasn't
the *model* surviving, it was Groq's free-tier **rate limit** throttling us. Recorded as-is,
it would have wrecked the Groq survival curves with dozens of fake early-censoring points.

The threat model's original rule censored *any* mid-run operational failure after a valid
round. That's fine for a rare one-off (OpenAI had exactly one), but under systematic
throttling it becomes a pollution source. So we **amended the operational rule** (transparently,
and based on a data-*quality* observation, not on the survival outcomes):

- **Transient failures** (rate-limit / connection / timeout) mid-run → **invalidate + reschedule**,
  never recorded. Operational artifacts are not survival data, so a throttled run gets re-run
  cleanly instead of polluting the curve.
- **Non-transient** failures after real data → still administrative censoring (rare, genuine).
- Plus a **patient rate-limit backoff**: honor the server's `Retry-After`, and wait out the
  per-minute window (up to 90s, 8 attempts) so most runs *complete* rather than failing.

We killed the polluting run, deleted the tainted Groq/Gemini data (OpenAI's clean 320 were
untouched), fixed the code (79 offline tests green), and re-ran clean.

**Lesson:** the deterministic detector was never fooled — the *pollution was in how we recorded
operational failures*, and it only showed up against a genuinely rate-limited free tier. An
automated harness must distinguish "the model held" from "the infrastructure failed," and log
the latter as a re-do, not a data point. Reading the raw CSV (not just the summary) is what
caught it.

## Phase 7 — Losing the key, and the replay-first demo

Mid-collection the **shared OpenAI account ran out of credit** (a billing wall, not a daily
reset) — which killed not just the remaining Target runs but the fixed `gpt-4o` *attacker*,
so no new live runs of any kind were possible. The important realization was how little this
actually threatened: the science was already done. Three models had complete, clean data
(gpt-3.5-turbo, gpt-4o-mini, gpt-5-nano — 480 runs, 24 cells), and **the entire analysis
layer is local** (survival curves, ASR heatmaps, log-rank all run off the saved CSV with no
API). The final report regenerated with zero network.

The one thing that genuinely needed a live attacker was the planned **live "Agent Duel" demo**.
So we pivoted the demo to **replay-first**: instead of attacking a model on stage, we animate
the **real saved transcripts** — 547 of them, 181 breaches and 299 clean holds — as an
attacker-vs-defender siege (a spear-wielding attacker, a shielded defender guarding a castle
that holds the secret). Breach → the castle falls and the leaked token is revealed; a 10-round
hold → the castle stands. It's a self-contained page (no server, no key, no internet), so it
**cannot fail live**, and every word on screen is genuine benchmark data rather than a scripted
mock. We curated four sieges: a roleplay confidentiality leak, a reactor override (integrity),
a 2025 small model that holds eight rounds then cracks, and a mid-tier model that refuses all
ten.

**Lesson:** a demo built on *replaying real results* is not a downgrade from a live demo — it's
more honest and more reliable. And keeping the analysis layer fully offline meant an
infrastructure failure that looked catastrophic ("the key is dead") cost us almost nothing on
the deliverables that mattered.

## Phase 8 — The secondary Judge, and figures for the presentation

With the primary (deterministic) results locked, we added the **secondary LLM-Judge** layer as
a *post-hoc* pass — deliberately **not** re-running the loop. A small tool reads each round's
saved Target reply from the transcripts, calls the isolated, brand-blind, canary-free Judge, and
writes a `judge_scores.csv`. Because the shared OpenAI key was dead, the Judge runs on **Gemini
free-tier** — which taught us its own lesson in quotas: a **15-requests-per-minute** cap and a
**500-requests-per-day** cap. Our first attempt hammered the per-minute wall and burned time on
57-second retry penalties; we fixed it by self-throttling to ~13/min, making the pass
**resumable** (skip already-scored rounds), **incremental** (flush every row), and
**model-balanced** (round-robin across the three models so the scarce gpt-3.5 rounds aren't
under-sampled). When the daily cap hit, we stopped cleanly, dropped the handful of unparseable
rows, and resumed the next day. The nice result: the Judge — a *separate* AI that never sees the
canary — independently rates the models in the **same robustness order** the deterministic
detector found (breach rounds score ~0.86 degradation vs ~0.33 on non-breach rounds). It
corroborates, but by design it can never *define* a breach.

For the deck we built a **figure gallery**. The first cut (matplotlib) worked but drifted into
inconsistency — the same model wore different colors in different charts, labels overlapped
error bars, and a couple of panels were redundant. We rebuilt the whole gallery in **Plotly**
under one design system: a single fixed per-model palette used in every panel, cleaned labels,
value labels lifted clear of the error bars, and the redundant/broken charts replaced. Each
figure was screenshot-verified before shipping.

**Lesson:** the Judge is a genuine *second opinion*, not a crutch — the primary metrics stand
without it, so a free-tier quota wall was an inconvenience, never a threat. And a figure is a
piece of communication: consistency (one color per model, everywhere) matters as much as the
numbers.

## Phase 9 — Publication: making the repository say what the project actually did

The science was finished; the *repository* wasn't. Read cold by someone who wasn't in the room,
it told a subtly wrong story — and every problem was the same problem: **the artifacts hadn't
caught up with the decisions.**

- **The config claimed five models; the data had three.** `experiment.yaml` still declared the
  full pre-credit-wall roster, so the analysis dutifully printed three `MISSING_CELL / nan`
  rows. That reads as a project cut short rather than one that was scoped. The fix was *not* to
  quietly delete the missing entries — that would have destroyed the pre-registration, which is
  the thing that makes the log-rank tests honest in the first place. Instead we split the two
  concerns: `experiment.yaml` now declares the **collected benchmark**, while the original
  locked declaration was frozen verbatim into `config/experiment.preregistered.yaml` — kept as
  a *runnable* config, not a quotation, so the appendix analysis reproduces the full declared
  hypothesis table with each pair marked `OK` or `NOT_COLLECTED`. Making the pre-registration
  executable turned out to be strictly better than merely archiving it.
- **The headline dataset had no generating script.** `rounds_3models.csv` — the file every
  published number came from — had been hand-filtered once and never again. We wrote
  `make_benchmark_subset.py` to derive it from the raw collection using the configured cell
  identity, and confirmed it reproduces the hand-made file byte-for-byte. That was the single
  worst reproducibility hole in the project.
- **None of the data was published.** A blanket `*.csv` rule in `.gitignore` had kept the entire
  480-trial dataset, all 547 transcripts and the figure gallery off GitHub. The demo only played
  at all because its baked `data.js` happened to be committed. We split **runtime scratch**
  (`output/`, `runs/` — still ignored) from the **published, frozen dataset** (`data/`,
  `results/` — committed), so a re-run can never overwrite data that cannot be regenerated.
- **The 24 "orphan" transcripts turned out to be evidence.** `transcripts/` held 24 more files
  than the CSV had runs. Every one ends in a `429 insufficient_quota` — they are the runs that
  were in flight when the billing wall hit, which the transient-failure rule from Phase 6
  correctly *invalidated instead of recording*. Rather than prune them, we documented them and
  wrote `verify_dataset.py` to assert that exact list, so an undocumented orphan now fails CI.
  What looked like mess was the audit trail for a rule we'd written months earlier.
- **A label bug hiding in plain sight.** The report mixed `gpt-3.5-turbo-0125` with
  `gpt-4o-mini`, because the prettifier stripped `-YYYY-MM-DD` but not `-MMDD` — and three
  copies of that function had drifted apart across `plots.py`, the figure script and the demo
  builder. Single-sourced into `analysis/labels.py`, with a test asserting all three call sites
  are the same object.

Everything was regenerated and diffed: **every ASR, CI, χ² and p-value is numerically identical**
to the pre-existing outputs — only model-label strings and the log-rank table changed. `make
reproduce` now rebuilds every published number, figure and demo payload offline from `data/`,
and CI runs the same path on every push and fails if the committed artifacts drift from what the
data produces.

**Lesson:** an incomplete result and a badly-presented result look identical from outside, and
only one of them is actually a problem. The work here wasn't hiding the credit wall — it was
making the repository state *the decisions* (what was scoped, what was declared, what was
discarded and why) instead of leaving a reader to infer them from a `nan`.

## Where things stand

- 81 offline tests green; the full pipeline drives end-to-end.
- Clean 3-model dataset (gpt-3.5-turbo, gpt-4o-mini, gpt-5-nano): 480 runs, 24 cells,
  181 breaches, 0 administratively censored. Headline ASR 92% / 14% / 8%; both computable
  pre-registered log-rank pairs separate at p < 0.001.
- Secondary Judge (Gemini) sample collected and figures generated; it corroborates the ranking.
- **Published and reproducible.** The dataset, transcripts, analysis and figure gallery are all
  committed; `make reproduce` regenerates every number and figure offline from `data/` with no
  API key, and CI enforces that on every push. The demo is served from GitHub Pages.
- Remaining, as future work: validating the Judge against a human gold set (Cohen's κ — the
  format is fixed in `gold_set/README.md` and the computation is a stub), and extending the
  roster beyond three same-vendor models if credit allows.

---

## Recurring themes (for the presentation)

- **Define the measurement before the machinery.** Our three worst latent bugs were all in
  metric definitions, caught in review.
- **A clean run is not a valid result.** The 0-breach pilot ran flawlessly and told us nothing
  useful — until we asked *why*.
- **Determinism has limits.** We can reproduce the experiment's structure, never the models'
  words. We say so explicitly.
- **Heterogeneity is the signal.** Survival analysis needs a spread of outcomes; that means a
  spread of model strengths, not just a strong attacker.
- **Fail loud.** Every rate limit, quota wall, and truncation is logged and surfaced, never
  silently coerced into a data point.
