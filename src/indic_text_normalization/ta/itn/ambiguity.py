"""
Number words that are also ordinary Tamil words, and the condition each needs.

Two conditions are needed because they are different context problems. A ``licensed``
word (ஒரு, ஓர் — also the indefinite article) is admitted only where a currency or clock
word inside the same token makes the reading numeric, which a token FST can express. A
``standalone`` word (கால் "leg", அரை "room/half-", முக்கால்) reads as a fraction on its own
but not before another Tamil word — that is a constraint on the *following* token, which a
token FST cannot see, so the prose tagger competes for the pair instead.
"""

from indic_text_normalization.core.utils import load_labels
from indic_text_normalization.ta.utils import get_abs_path

LICENSED = "licensed"
STANDALONE = "standalone"


def ambiguous_words(condition: str) -> list[tuple[str, str]]:
    """
    The ``(word, reading)`` pairs whose admission condition is ``condition``.
    """
    rows = load_labels(get_abs_path("data/numbers/itn_ambiguous.tsv"), min_fields=3)
    return [(word, reading) for word, row_condition, reading in rows if row_condition == condition]
