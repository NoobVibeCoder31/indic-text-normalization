"""
ITN tagger converting spoken Tamil ordinals to digits with an ordinal suffix.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import CHAR, GraphFst, sequential
from indic_text_normalization.ta.constants import TA_LETTER
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class OrdinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken ordinals, e.g.
        ஐந்தாவது -> ordinal { integer: "5" morphosyntactic_features: "வது" }
        பத்தாம் -> ordinal { integer: "10" morphosyntactic_features: "ஆம்" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="classify", deterministic=deterministic)

        # Undo the adjectival stem: the cardinal's final -உ becomes -ஆ and a ம்-final
        # scale word becomes -மா (ஐந்து -> ஐந்தா, ஆயிரம் -> ஆயிரமா, நூறு -> நூற்றா).
        to_cardinal = pynini.closure(CHAR) + pynini.union(
            pynini.cross("ா", "ு"),
            pynini.cross("மா", "ம்"),
            pynini.cross("ற்றா", "று"),
        )
        stem = sequential((to_cardinal @ cardinal.words_to_digits) | pynini.cross("முதலா", "1"))

        integer = pynutil.insert('integer: "') + stem + pynutil.insert('"')

        # -வது plus any inflected tail: ஐந்தாவது -> 5வது, ஐந்தாவதுக்கு -> 5வதுக்கு.
        graph_vathu = (
            integer
            + pynutil.insert(' morphosyntactic_features: "')
            + pynini.accep("வத")
            + pynini.closure(TA_LETTER, 1)
            + pynutil.insert('"')
        )
        graph_aam = (
            integer + pynutil.insert(' morphosyntactic_features: "ஆம்"') + pynutil.delete("ம்")
        )

        graph = (graph_vathu | graph_aam) + pynutil.insert(" preserve_order: true")
        self.fst = self.add_tokens(graph).optimize()
