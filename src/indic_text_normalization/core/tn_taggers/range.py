"""
TN tagger for numeric ranges like 10-20, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase


class RangeFst(GraphFst):
    """
    Finite state transducer for classifying numeric ranges, e.g.
        10-20 -> range { lower: "పది" upper: "ఇరవై" }
        10-20లో -> range { lower: "పది" upper: "ఇరవైలో" }
    """

    def __init__(self, cardinal: CardinalBase, deterministic: bool = True) -> None:
        super().__init__(name="range", kind="classify", deterministic=deterministic)

        graph = (
            pynutil.insert('lower: "')
            + cardinal.final_graph
            + pynutil.insert('"')
            + pynutil.delete(pynini.closure(" ", 0, 1) + "-" + pynini.closure(" ", 0, 1))
            + pynutil.insert(' upper: "')
            + (
                cardinal.final_graph
                | pynutil.add_weight(cardinal.attach_case_suffix(cardinal.final_graph), 0.1)
            )
            + pynutil.insert('"')
            + pynutil.insert(" preserve_order: true")
        )
        self.fst = self.add_tokens(graph).optimize()
