"""
Malayalam TN fraction verbalizer.
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
from indic_text_normalization.ml.constants import MINUS, SUFFIX_MARK
from indic_text_normalization.ml.morphology import suffix_sandhi

# The denominator takes the locative (നാല് -> നാലിൽ); a mixed number joins its parts with
# -ും on each (രണ്ടും നാലിൽ മൂന്നും).
LOCATIVE = ((SIGMA + pynutil.insert(SUFFIX_MARK + "ിൽ")) @ suffix_sandhi()).optimize()
UM = ((SIGMA + pynutil.insert(SUFFIX_MARK + "ും")) @ suffix_sandhi()).optimize()


class FractionFst(GraphFst):
    """
    Finite state transducer for verbalizing fractions, e.g.
        fraction { numerator: "മൂന്ന്" denominator: "നാല്" } -> നാലിൽ മൂന്ന്
        fraction { integer_part: "രണ്ട്" numerator: "മൂന്ന്" denominator: "നാല്" } -> രണ്ടും നാലിൽ മൂന്നും
        fraction { word: "ഒന്നര" } -> ഒന്നര
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="verbalize", deterministic=deterministic)

        value = pynini.closure(NOT_QUOTE, 1)
        denominator = pynutil.delete('denominator: "') + (value @ LOCATIVE) + pynutil.delete('"')
        numerator = pynutil.delete('numerator: "') + value + pynutil.delete('"')
        numerator_um = pynutil.delete('numerator: "') + (value @ UM) + pynutil.delete('"')
        integer_um = pynutil.delete('integer_part: "') + (value @ UM) + pynutil.delete('"')

        graph = denominator + delete_space + insert_space + numerator
        graph |= (
            integer_um
            + delete_space
            + insert_space
            + denominator
            + delete_space
            + insert_space
            + numerator_um
        )
        word = pynutil.delete('word: "') + value + pynutil.delete('"')

        optional_sign = pynini.closure(pynini.cross('negative: "true"', MINUS) + delete_space, 0, 1)
        self.fst = self.delete_tokens(optional_sign + (graph | word)).optimize()
