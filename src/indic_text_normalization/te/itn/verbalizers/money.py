"""
ITN verbalizer emitting written money amounts.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import (
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
)


class MoneyFst(GraphFst):
    """
    Finite state transducer for verbalizing money, e.g.
        money { currency: "₹" integer_part: "50" fractional_part: "50" } -> ₹50.50
        money { currency: "₹" integer_part: "50" suffix: "కి" } -> ₹50కి
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
        suffix = pynini.closure(
            delete_space
            + pynutil.delete('suffix: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"'),
            0,
            1,
        )

        optional_sign = pynini.closure(pynini.cross('negative: "true"', "-") + delete_space, 0, 1)
        self.graph = (
            optional_sign
            + currency
            + delete_space
            + integer
            + pynini.closure(delete_space + pynutil.insert(".") + fraction, 0, 1)
            + suffix
            + delete_preserve_order
        )
        self.fst = self.delete_tokens(self.graph).optimize()
