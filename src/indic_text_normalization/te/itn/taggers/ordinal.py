"""
ITN tagger converting spoken Telugu ordinals to digits with the written -వ marker.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst
from indic_text_normalization.te.constants import TE_LETTER, TE_TO_ASCII_DIGIT
from indic_text_normalization.te.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.te.tn.taggers.cardinal import (
    ORDINAL_TAILS,
    CardinalFst as TnCardinalFst,
    ordinal_graph,
)


class OrdinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken ordinals, e.g.
        ఐదవ -> ordinal { integer: "5వ" }
        మొదటిది -> ordinal { integer: "1వది" }
    """

    def __init__(
        self, cardinal: CardinalFst, tn_cardinal: TnCardinalFst, deterministic: bool = True
    ) -> None:
        super().__init__(name="ordinal", kind="classify", deterministic=deterministic)

        # Invert the TN ordinal reading: spoken stem + వ (+ tail) -> digits + వ (+ tail).
        # The colloquial -ో reading is written with the plain -వ marker.
        to_ascii = (
            pynini.closure(pynini.union(TE_TO_ASCII_DIGIT, DIGIT))
            + (pynini.cross("వో", "వ") | pynini.accep("వ"))
            + pynini.closure(TE_LETTER)
        )
        readable = pynini.union(tn_cardinal.final_graph, tn_cardinal.graph_year_hundreds)
        inverted = (pynini.invert(ordinal_graph(readable)) @ to_ascii).optimize()
        tails = pynini.union(*[pynini.accep(t) for t in ORDINAL_TAILS])
        first = pynini.cross("మొదటి", "1వ") + tails

        graph = pynutil.insert('integer: "') + cardinal.read(inverted | first) + pynutil.insert('"')
        self.fst = self.add_tokens(graph).optimize()
