"""
TN tagger for numeric ranges like 10-20.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst


class RangeFst(GraphFst):
    """
    Finite state transducer for classifying numeric ranges, e.g.
        10-20 -> range { lower: "பத்து" upper: "இருபது" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="range", kind="classify", deterministic=deterministic)

        graph = (
            pynutil.insert('lower: "')
            + cardinal.final_graph
            + pynutil.insert('"')
            + pynutil.delete(pynini.closure(" ", 0, 1) + "-" + pynini.closure(" ", 0, 1))
            + pynutil.insert(' upper: "')
            + cardinal.final_graph
            + pynutil.insert('"')
            + pynutil.insert(" preserve_order: true")
        )
        self.fst = self.add_tokens(graph).optimize()
