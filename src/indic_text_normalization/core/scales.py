"""
Scale words and how the ITN grammars read a decimal amount that carries one.
"""

from indic_text_normalization.core.utils import data_path, load_labels

_EXPAND = "expand"


def scale_words(lang: str) -> list[tuple[str, int, str]]:
    """
    The scale words of ``lang`` as ``(word, trailing zeros, policy)`` triples.
    """
    rows = load_labels(data_path(lang, "numbers/scale_words.tsv"), min_fields=3)
    return [(word, int(zeros), policy) for word, zeros, policy in rows]


def kept_scale_words(lang: str) -> list[str]:
    """
    Scale words a written amount keeps as a word (5.5 லட்சம், ₹2.5 కోట్లు).
    """
    return [word for word, _, policy in scale_words(lang) if policy != _EXPAND]


def expanded_scale_words(lang: str) -> list[tuple[str, int]]:
    """
    Scale words small enough to multiply out instead, as ``(word, trailing zeros)``.
    """
    return [(word, zeros) for word, zeros, policy in scale_words(lang) if policy == _EXPAND]
