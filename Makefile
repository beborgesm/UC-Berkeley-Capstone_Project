# BreachBenchmark — common tasks.
#
# Everything except `judge` runs OFFLINE against the committed dataset in data/:
# no API key, no network. `make reproduce` regenerates every published number and figure.

# python3 rather than python: macOS ships no bare `python`, so the default has to be the
# one that exists everywhere. Override with `make install PY=python3.13` to pin a version.
PY      ?= python3
VENV    ?= .venv
# Command prefix, WITH trailing slash. Override with `BIN=` to use whatever is on PATH
# (that is what CI does, since it installs into the runner's own environment).
BIN     ?= $(VENV)/bin/
# Strip vendor keys so the offline guarantee is enforced, not just asserted.
NOKEYS  := env -u OPENAI_API_KEY -u GEMINI_API_KEY -u GROQ_API_KEY

.DEFAULT_GOAL := help
.PHONY: help install test verify analysis figures demo-data reproduce reproduce-nofigs demo subset judge clean

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Create the venv and install the package with analysis + figure extras
	$(PY) -m venv $(VENV)
	$(BIN)pip install --upgrade pip
	$(BIN)pip install -e ".[analysis,figures,dev]"

test:  ## Run the offline test suite with all API keys stripped from the env
	$(NOKEYS) $(BIN)python -m pytest tests/ -q

verify:  ## Check the published dataset matches its documented state
	$(BIN)python scripts/verify_dataset.py

analysis:  ## KM curves, ASR tables, log-rank -> results/analysis{,_extended}
	$(BIN)breachbench-analyze \
		--rounds-csv data/rounds_benchmark.csv --out results/analysis
	$(BIN)breachbench-analyze --config config/experiment.preregistered.yaml \
		--rounds-csv data/rounds_raw.csv --out results/analysis_extended

figures:  ## Slide-ready Plotly gallery -> results/figures
	$(BIN)python scripts/make_figures.py

demo-data:  ## Bake the curated transcripts into demo/replay/data.js
	$(BIN)python demo/build_replay_data.py

reproduce: verify analysis figures demo-data  ## Regenerate every published artifact, offline
	@echo
	@echo "Reproduced from data/ with no API key and no network:"
	@echo "  results/analysis/REPORT.md   results/figures/   demo/replay/data.js"

# Same, minus the figure gallery: kaleido drives a headless Chromium to export the PNGs,
# which is a browser dependency CI shouldn't need. Everything else is pure Python.
reproduce-nofigs: verify analysis demo-data  ## reproduce without the browser-dependent figure export
	@echo "Reproduced analysis + demo data (figures skipped: no headless browser)."

demo:  ## Open the offline siege replay in a browser
	@open demo/replay/index.html 2>/dev/null || xdg-open demo/replay/index.html

subset:  ## Re-derive data/rounds_benchmark.csv from the raw collection
	$(BIN)python scripts/make_benchmark_subset.py

judge:  ## SECONDARY, needs GEMINI_API_KEY. Resumable post-hoc Judge pass (optional)
	$(BIN)python scripts/judge_transcripts.py

clean:  ## Remove caches and runtime scratch (never touches data/ or results/)
	rm -rf .pytest_cache **/__pycache__ src/**/__pycache__ .coverage htmlcov
