"""
Scale words and how the ITN grammars read a decimal amount that carries one.
"""

from indic_text_normalization.core.utils import load_labels
from indic_text_normalization.ta.utils import get_abs_path

_EXPAND = "expand"


def scale_words() -> list[tuple[str, int, str]]:
    """
    The scale words as ``(word, trailing zeros, policy)`` triples.
    """
    rows = load_labels(get_abs_path("data/numbers/scale_words.tsv"), min_fields=3)
    return [(word, int(zeros), policy) for word, zeros, policy in rows]


def kept_scale_words() -> list[str]:
    """
    Scale words a decimal amount keeps in writing (5.5 லட்சம், ₹2.5 கோடி).
    """
    return [word for word, _, policy in scale_words() if policy != _EXPAND]


def expanded_scale_words() -> list[tuple[str, int]]:
    """
    Scale words small enough to multiply out instead, as ``(word, trailing zeros)``.
    """
    return [(word, zeros) for word, zeros, policy in scale_words() if policy == _EXPAND]
