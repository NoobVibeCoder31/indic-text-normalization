"""
ITN verbalizer emitting written fractions.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import NOT_QUOTE, GraphFst, delete_space


class FractionFst(GraphFst):
    """
    Finite state transducer for verbalizing fractions, e.g.
        fraction { numerator: "3" denominator: "4" } -> 3/4
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="verbalize", deterministic=deterministic)

        numerator = (
            pynutil.delete('numerator: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        denominator = (
            pynutil.delete('denominator: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )

        self.graph = numerator + delete_space + pynutil.insert("/") + denominator
        self.fst = self.delete_tokens(self.graph).optimize()
