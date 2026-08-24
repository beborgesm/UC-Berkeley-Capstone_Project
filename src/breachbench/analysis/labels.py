"""Canonical display labels for models.

The harness records the *resolved* model version an endpoint reports back
(`gpt-4o-mini-2024-07-18`, `gpt-3.5-turbo-0125`), because that is what was actually served
and is the reproducibility-relevant value. Those strings are correct in the data and wrong in
a figure legend, a report table or a demo nameplate — and they use *two* different suffix
conventions, so a partial normalisation reads worse than none at all (a table mixing
`gpt-3.5-turbo-0125` with `gpt-4o-mini` looks like an inconsistency rather than a version).

This module is the single implementation. The raw columns are never mutated; labels are
applied at render time only, so `data/` and the analysis inputs stay verbatim.
"""

from __future__ import annotations

import re

# Both suffix conventions OpenAI uses for a resolved snapshot.
_DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")  # -2024-07-18
_SNAPSHOT_SUFFIX = re.compile(r"-\d{4}$")  # -0125


def prettify_model(name: str) -> str:
    """Strip a resolved-version suffix for display.

    >>> prettify_model("gpt-4o-mini-2024-07-18")
    'gpt-4o-mini'
    >>> prettify_model("gpt-3.5-turbo-0125")
    'gpt-3.5-turbo'
    >>> prettify_model("gpt-5-nano")
    'gpt-5-nano'
    """
    out = _DATE_SUFFIX.sub("", str(name or ""))
    return _SNAPSHOT_SUFFIX.sub("", out)
