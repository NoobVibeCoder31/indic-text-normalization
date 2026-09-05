"""
FAR grammar caching. All FAR file naming lives here.
"""

from pathlib import Path

import pynini

from indic_text_normalization.core.graph_utils import generator_main

CLASSIFY_RULE = "tokenize_and_classify"
VERBALIZE_RULE = "verbalize"


def far_path(cache_dir: str | Path, lang: str, direction: str) -> Path:
    """
    Return the FAR file path for a compiled ``(lang, direction)`` grammar pair.
    """
    return Path(cache_dir) / f"{lang}_{direction}.far"


def load(path: Path) -> tuple[pynini.Fst, pynini.Fst] | None:
    """
    Load ``(classify, verbalize)`` FSTs from a FAR file, or None if unreadable.
    """
    if not path.exists():
        return None
    try:
        far = pynini.Far(str(path), mode="r")
        classify = far[CLASSIFY_RULE]
        far.reset()
        verbalize = far[VERBALIZE_RULE]
        return classify, verbalize
    except Exception:
        return None


def save(path: Path, classify: pynini.Fst, verbalize: pynini.Fst) -> None:
    """
    Write ``(classify, verbalize)`` FSTs to a FAR file, creating parent dirs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    generator_main(str(path), {CLASSIFY_RULE: classify, VERBALIZE_RULE: verbalize})
