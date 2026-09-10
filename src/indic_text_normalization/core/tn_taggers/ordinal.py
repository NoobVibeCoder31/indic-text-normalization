"""
TN tagger for written ordinals, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase


class OrdinalFst(GraphFst):
    """
    Finite state transducer for classifying ordinals, e.g.
        5వ -> ordinal { integer: "ఐదవ" }
        1వ -> ordinal { integer: "మొదటి" }

    Attributes
    ----------
    cardinal : ``CardinalBase``
        The language's cardinal; its ``ordinal_graph`` reads the regular forms.
    exceptions : ``pynini.Fst | None``, optional (default = None)
        Irregular ordinals as a transducer from the written form (digits, marker and
        tail) to the spoken word (1వ -> మొదటి, 1ನೇ -> ಮೊದಲನೇ). They outrank the regular reading.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: CardinalBase,
        *,
        exceptions: pynini.Fst | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="ordinal", kind="classify", deterministic=deterministic)

        graph = cardinal.ordinal_graph(cardinal.final_graph)
        if exceptions is not None:
            graph = pynini.union(graph, pynutil.add_weight(exceptions, -0.1))

        final_graph = pynutil.insert('integer: "') + graph + pynutil.insert('"')
        self.fst = self.add_tokens(final_graph).optimize()
