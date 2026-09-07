"""
ITN verbalizer emitting written decimals.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import NOT_QUOTE, GraphFst, delete_space


class DecimalFst(GraphFst):
    """
    Finite state transducer for verbalizing decimals, e.g.
        decimal { integer_part: "12" fractional_part: "5" } -> 12.5
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="verbalize", deterministic=deterministic)

        optional_sign = pynini.closure(pynini.cross('negative: "true"', "-") + delete_space, 0, 1)
        integer = (
            pynutil.delete('integer_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        fraction = (
            pynutil.delete('fractional_part: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )

        self.graph = optional_sign + integer + delete_space + pynutil.insert(".") + fraction
        self.fst = self.delete_tokens(self.graph).optimize()
