"""
Hindi TN fraction verbalizer.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    NOT_QUOTE,
    GraphFst,
    delete_space,
)
from indic_text_normalization.hi.constants import AND_WORD, MINUS_WORD

BY_WORD = "बटा"


class FractionFst(GraphFst):
    """
    Finite state transducer for verbalizing fractions, e.g.
        fraction { numerator: "तीन" denominator: "चार" } -> तीन बटा चार
        fraction { integer_part: "दो" numerator: "तीन" denominator: "चार" } -> दो पूर्णांक तीन बटा चार
        fraction { word: "डेढ़" } -> डेढ़
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="verbalize", deterministic=deterministic)

        value = pynini.closure(NOT_QUOTE, 1)
        numerator = pynutil.delete('numerator: "') + value + pynutil.delete('"')
        denominator = pynutil.delete('denominator: "') + value + pynutil.delete('"')
        integer = pynutil.delete('integer_part: "') + value + pynutil.delete('"')

        graph = numerator + delete_space + pynutil.insert(f" {BY_WORD} ") + denominator
        graph = (
            pynini.closure(integer + delete_space + pynutil.insert(f" {AND_WORD} "), 0, 1) + graph
        )
        word = pynutil.delete('word: "') + value + pynutil.delete('"')

        optional_sign = pynini.closure(
            pynini.cross('negative: "true"', f" {MINUS_WORD} ") + delete_space, 0, 1
        )
        self.fst = self.delete_tokens(optional_sign + (graph | word)).optimize()
