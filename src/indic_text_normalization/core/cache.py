"""
FAR grammar caching. All FAR file naming lives here.
"""

import hashlib
from contextlib import suppress
from functools import cache as _memoize
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pynini

from indic_text_normalization.core.graph_utils import generator_main

CLASSIFY_RULE = "tokenize_and_classify"
VERBALIZE_RULE = "verbalize"

# Files whose contents decide what a compiled grammar contains.
_SOURCE_SUFFIXES = (".py", ".tsv")


@_memoize
def grammar_digest(lang: str) -> str:
    """
    Short digest of the package version and the sources a ``lang`` grammar compiles from.

    Parameters
    ----------
    lang : ``str``
        Language code whose package is hashed, alongside ``core``.

    Returns
    -------
    ``str``
        Sixteen hex characters identifying this grammar build.
    """
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    # An uninstalled source tree has no distribution metadata; the file hashes below
    # still identify the grammar.
    with suppress(PackageNotFoundError):
        digest.update(version("indic-text-normalization").encode())
    for sub in ("core", lang):
        for path in sorted((root / sub).rglob("*")):
            if path.is_file() and path.suffix in _SOURCE_SUFFIXES:
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def far_path(cache_dir: str | Path, lang: str, direction: str) -> Path:
    """
    Return the FAR file path for a compiled ``(lang, direction)`` grammar pair.

    The path is keyed by :func:`grammar_digest`, so a FAR written by an older version of
    the package or grammar is never silently reused after an upgrade.
    """
    return Path(cache_dir) / grammar_digest(lang) / f"{lang}_{direction}.far"


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
