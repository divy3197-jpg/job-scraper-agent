"""Fast keyword pre-filter — eliminates obvious mismatches before the AI runs."""
import yaml
from pathlib import Path

_config = None


def _load():
    global _config
    if _config is None:
        _config = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text())
    return _config


def is_relevant(text: str) -> bool:
    """Return False if text matches blocked keywords or misses required ones."""
    cfg = _load()
    f = cfg.get("filters", {})
    blocked = [k.lower() for k in f.get("blocked_keywords", [])]
    required = [k.lower() for k in f.get("required_keywords", [])]
    t = text.lower()

    if any(k in t for k in blocked):
        return False
    if required and not any(k in t for k in required):
        return False
    return True
