"""
ITN verbalizer emitting written cardinals.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import NOT_QUOTE, GraphFst, delete_space


class CardinalFst(GraphFst):
    """
    Finite state transducer for verbalizing cardinals, e.g.
        cardinal { negative: "true" integer: "120" } -> -120
        cardinal { positive: "true" integer: "5" } -> +5
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="cardinal", kind="verbalize", deterministic=deterministic)

        optional_sign = pynini.closure(
            (pynini.cross('negative: "true"', "-") | pynini.cross('positive: "true"', "+"))
            + delete_space,
            0,
            1,
        )
        integer = pynutil.delete('integer: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')

        self.graph = optional_sign + integer
        self.fst = self.delete_tokens(self.graph).optimize()
