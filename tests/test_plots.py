"""Smoke tests for the figure/report layer (matplotlib Agg, no network)."""

from __future__ import annotations

import numpy as np

from breachbench.analysis.asr import asr_table
from breachbench.analysis.loader import CellObservations
from breachbench.analysis.plots import (
    generate_figures,
    prettify_model,
    summary_table_markdown,
)


def _cells():
    return [
        CellObservations(cell_id="c1", target_vendor="openai",
                         target_model_version="gpt-3.5-turbo-0125", scenario_id="conf_vault_v1",
                         attack_vector="CIPHER",
                         durations=np.array([2, 2, 3, 4, 10]), events=np.array([1, 1, 1, 1, 0])),
        CellObservations(cell_id="c2", target_vendor="openai",
                         target_model_version="gpt-4o-mini-2024-07-18", scenario_id="conf_vault_v1",
                         attack_vector="CIPHER",
                         durations=np.array([10, 10, 10, 8, 10]), events=np.array([0, 0, 0, 1, 0])),
    ]


def test_prettify_model_strips_date():
    assert prettify_model("gpt-4o-mini-2024-07-18") == "gpt-4o-mini"
    assert prettify_model("llama-3.1-8b-instant") == "llama-3.1-8b-instant"


def test_prettify_model_strips_snapshot_suffix():
    """OpenAI uses TWO resolved-version conventions. Normalizing only the dated one left
    tables mixing 'gpt-3.5-turbo-0125' with 'gpt-4o-mini', which reads as an inconsistency
    rather than a version — so the -MMDD form must be stripped too."""
    assert prettify_model("gpt-3.5-turbo-0125") == "gpt-3.5-turbo"
    assert prettify_model("gpt-5-nano") == "gpt-5-nano"
    # A version-free name that happens to end in digits must survive untouched.
    assert prettify_model("gpt-4o") == "gpt-4o"
    assert prettify_model("") == ""


def test_prettify_model_is_single_sourced():
    """plots.py, the figure scripts and the demo builder must all use one implementation —
    three private copies is how the labels drifted apart in the first place."""
    from breachbench.analysis import prettify_model as exported
    from breachbench.analysis.labels import prettify_model as canonical
    from breachbench.analysis.plots import prettify_model as via_plots

    assert canonical is via_plots is exported


def test_summary_table_markdown_has_rows():
    cells = _cells()
    table = asr_table(cells, k_max=10, bootstrap_B=50)
    md = summary_table_markdown(table)
    assert md.startswith("| scenario")
    assert "gpt-3.5-turbo" in md and "gpt-4o-mini" in md


def test_generate_figures_writes_pngs(tmp_path):
    cells = _cells()
    table = asr_table(cells, k_max=10, bootstrap_B=50)
    paths = generate_figures(cells, table, k_max=10, out_dir=tmp_path, bootstrap_B=50)
    assert paths
    assert (tmp_path / "km_conf_vault_v1.png").exists()
    assert (tmp_path / "asr_heatmap_conf_vault_v1.png").exists()
    for p in paths:
        assert p.stat().st_size > 0
