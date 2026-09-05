"""
ITN verbalizer emitting written ordinals.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
)


class OrdinalFst(GraphFst):
    """
    Finite state transducer for verbalizing ordinals, e.g.
        ordinal { integer: "5" morphosyntactic_features: "வது" } -> 5வது
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="verbalize", deterministic=deterministic)

        integer = pynutil.delete('integer: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        suffix = (
            pynutil.delete('morphosyntactic_features: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )

        self.graph = integer + delete_space + suffix + delete_preserve_order
        self.fst = self.delete_tokens(self.graph).optimize()
