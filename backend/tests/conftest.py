import os

# Force the offline, deterministic provider for all tests (also the default).
os.environ.setdefault("LLM_PROVIDER", "fake")
