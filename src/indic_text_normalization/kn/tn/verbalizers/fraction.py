"""
Kannada TN fraction verbalizer.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    NOT_QUOTE,
    SIGMA,
    GraphFst,
    delete_space,
    insert_space,
)
from indic_text_normalization.kn.constants import AND_WORD, MINUS_WORD, SUFFIX_MARK
from indic_text_normalization.kn.morphology import suffix_sandhi

# The denominator takes the locative (ನಾಲ್ಕು -> ನಾಲ್ಕರಲ್ಲಿ).
LOCATIVE = ((SIGMA + pynutil.insert(SUFFIX_MARK + "ರಲ್ಲಿ")) @ suffix_sandhi()).optimize()


class FractionFst(GraphFst):
    """
    Finite state transducer for verbalizing fractions, e.g.
        fraction { numerator: "ಮೂರು" denominator: "ನಾಲ್ಕು" } -> ನಾಲ್ಕರಲ್ಲಿ ಮೂರು
        fraction { integer_part: "ಎರಡು" numerator: "ಮೂರು" denominator: "ನಾಲ್ಕು" } -> ಎರಡು ಮತ್ತು ನಾಲ್ಕರಲ್ಲಿ ಮೂರು
        fraction { word: "ಒಂದೂವರೆ" } -> ಒಂದೂವರೆ
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="verbalize", deterministic=deterministic)

        value = pynini.closure(NOT_QUOTE, 1)
        denominator = pynutil.delete('denominator: "') + (value @ LOCATIVE) + pynutil.delete('"')
        numerator = pynutil.delete('numerator: "') + value + pynutil.delete('"')
        integer = pynutil.delete('integer_part: "') + value + pynutil.delete('"')

        graph = denominator + delete_space + insert_space + numerator
        graph = (
            pynini.closure(integer + delete_space + pynutil.insert(f" {AND_WORD} "), 0, 1) + graph
        )
        word = pynutil.delete('word: "') + value + pynutil.delete('"')

        optional_sign = pynini.closure(
            pynini.cross('negative: "true"', f" {MINUS_WORD} ") + delete_space, 0, 1
        )
        self.fst = self.delete_tokens(optional_sign + (graph | word)).optimize()
