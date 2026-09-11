"""
Scale ("quantity") words a number may carry, loaded from ``numbers/quantity_words.tsv``.
"""

from dataclasses import dataclass

import pynini

from indic_text_normalization.core.utils import data_path, load_labels

NATIVE = "native"
ENGLISH = "english"
SHORT = "short"


@dataclass(frozen=True)
class QuantityWords:
    """
    The written quantity words of one language, grouped by how they attach to a number.

    Attributes
    ----------
    spaced : ``pynini.Fst``
        Native and English words that follow the number after a space, mapped to their
        spoken form (కోట్లు -> కోట్లు, lakh -> లక్షలు).
    short : ``pynini.Fst``
        Shorthands that may be glued to the number (L, cr, K, M), mapped to the spoken word.
    native : ``pynini.Fst``
        Native words only, for a second stacked scale word (₹1 లక్ష కోట్లు).
    """

    spaced: pynini.Fst
    short: pynini.Fst
    native: pynini.Fst


def quantity_words(lang: str) -> QuantityWords:
    """
    Load ``numbers/quantity_words.tsv`` (written, spoken, kind) for ``lang``.
    """
    rows = load_labels(data_path(lang, "numbers/quantity_words.tsv"), min_fields=3)
    by_kind: dict[str, list[tuple[str, str]]] = {NATIVE: [], ENGLISH: [], SHORT: []}
    for written, spoken, kind in rows:
        by_kind[kind].append((written, spoken))
    native = pynini.string_map(by_kind[NATIVE]).optimize()
    return QuantityWords(
        spaced=pynini.union(native, pynini.string_map(by_kind[ENGLISH])).optimize(),
        short=pynini.string_map(by_kind[SHORT]).optimize(),
        native=native,
    )
