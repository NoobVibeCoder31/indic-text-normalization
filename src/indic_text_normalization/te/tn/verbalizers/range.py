"""
TN verbalizer for numeric ranges.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import (
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
)


class RangeFst(GraphFst):
    """
    Finite state transducer for verbalizing ranges, e.g.
        range { lower: "పది" upper: "ఇరవై" } -> పది నుండి ఇరవై
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="range", kind="verbalize", deterministic=deterministic)

        lower = pynutil.delete('lower: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        upper = pynutil.delete('upper: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')

        graph = lower + delete_space + pynutil.insert(" నుండి ") + upper + delete_preserve_order
        self.fst = self.delete_tokens(graph).optimize()
