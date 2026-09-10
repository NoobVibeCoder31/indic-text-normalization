"""
ITN tagger converting spoken ordinals to digits with the written marker, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.itn_taggers.cardinal import ItnCardinalFst
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase


class ItnOrdinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken ordinals, e.g.
        ఐదవ -> ordinal { integer: "5వ" }
        మొదటిది -> ordinal { integer: "1వది" }

    Attributes
    ----------
    cardinal : ``ItnCardinalFst``
        The language's ITN cardinal (for its pre-map).
    tn_cardinal : ``CardinalBase``
        The language's TN cardinal, whose ordinal reading is inverted.
    marker : ``pynini.Fst``
        The written marker after the digits, as a transducer over the TN ordinal's own
        marker text (Telugu writes -వ for both -వ and the colloquial -వో).
    exceptions : ``pynini.Fst | None``, optional (default = None)
        Irregular spoken ordinals to their written form (మొదటి -> 1వ), tails included.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: ItnCardinalFst,
        tn_cardinal: CardinalBase,
        *,
        marker: pynini.Fst,
        exceptions: pynini.Fst | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="ordinal", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        to_written = profile.to_ascii + marker + pynini.closure(profile.letter)
        inverted = (
            pynini.invert(tn_cardinal.ordinal_graph(tn_cardinal.readable_years())) @ to_written
        ).optimize()
        if exceptions is not None:
            inverted |= exceptions

        graph = pynutil.insert('integer: "') + cardinal.read(inverted) + pynutil.insert('"')
        self.fst = self.add_tokens(graph).optimize()
