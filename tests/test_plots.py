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
