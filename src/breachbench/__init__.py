"""BreachBenchmark — deterministic-first, closed-loop LLM red-teaming harness.

Importing this package must NOT construct any vendor SDK client, read any API
key, or touch the network. Everything heavy is imported lazily inside the module
that needs it. Keep this file minimal.
"""

__version__ = "0.1.0"
SCHEMA_VERSION = "1.0"

__all__ = ["__version__", "SCHEMA_VERSION"]
