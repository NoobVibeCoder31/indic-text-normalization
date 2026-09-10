"""
Fused Tamil fraction words (ஒன்றரை, பத்தே கால்) shared by the ITN decimal, money and
time grammars.
"""

from collections.abc import Callable

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.core.graph_utils import CHAR
from indic_text_normalization.ta.constants import LANG, TA_ARAI, TA_KAAL, TA_MUKKAL

# Fraction digits of the quarter words, and the same quantity read as clock minutes.
QUARTER_FRACTION = {TA_KAAL: "25", TA_ARAI: "5", TA_MUKKAL: "75"}
FRACTION_MINUTES = {"5": "30", "25": "15", "75": "45"}


def half_form_rows() -> list[tuple[str, str, str]]:
    """
    The fused half/quarter words as ``(word, integer, fraction)`` triples.
    """
    rows = load_labels(data_path(LANG, "numbers/itn_half_forms.tsv"), min_fields=3)
    return [(word, ip, fp) for word, ip, fp in rows]


def quarter_form_graph(
    number: pynini.Fst, *, prefix: str, infix: str, suffix: Callable[[str], str]
) -> pynini.Fst:
    """
    Map an -ே linked quarter phrase (பத்தே கால், ஒன்றேகால்) to ``prefix INT infix suffix(frac)``.
    """
    stem = ((pynini.closure(CHAR) + pynini.cross("ே", "ு")) @ number).optimize()
    optional_space = pynini.closure(pynutil.delete(" "), 0, 1)
    return pynini.union(
        *[
            pynutil.insert(prefix)
            + stem
            + pynutil.insert(infix)
            + optional_space
            + pynutil.delete(word)
            + pynutil.insert(suffix(fraction))
            for word, fraction in QUARTER_FRACTION.items()
        ]
    ).optimize()
