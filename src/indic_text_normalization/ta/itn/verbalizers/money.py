"""
ITN verbalizer emitting written money amounts.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import NOT_QUOTE, GraphFst, delete_space


class MoneyFst(GraphFst):
    """
    Finite state transducer for verbalizing money, e.g.
        money { currency: "₹" integer_part: "50" fractional_part: "50" } -> ₹50.50
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="money", kind="verbalize", deterministic=deterministic)

        currency = (
            pynutil.delete('currency: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        integer = (
            pynutil.delete('integer_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        fraction = (
            pynutil.delete('fractional_part: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )

        self.graph = (
            currency
            + delete_space
            + integer
            + pynini.closure(delete_space + pynutil.insert(".") + fraction, 0, 1)
        )
        self.fst = self.delete_tokens(self.graph).optimize()
