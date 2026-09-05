"""
ITN tagger converting spoken Tamil ordinals to digits with an ordinal suffix.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import CHAR, GraphFst
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class OrdinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken ordinals, e.g.
        ஐந்தாவது -> ordinal { integer: "5" morphosyntactic_features: "வது" }
        பத்தாம் -> ordinal { integer: "10" morphosyntactic_features: "ஆம்" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="classify", deterministic=deterministic)

        # Undo the adjectival stem: -ாவது / -ாம் back to the cardinal's -உ / -ம் ending.
        sigma = pynini.closure(CHAR)
        to_cardinal_vathu = sigma + pynini.cross("ாவது", "ு")
        to_cardinal_aam = sigma + pynini.cross("ாம்", "ு")
        first_vathu = pynini.cross("முதலாவது", "ஒன்று")
        first_aam = pynini.cross("முதலாம்", "ஒன்று")

        graph_vathu = (
            pynutil.insert('integer: "')
            + (
                (to_cardinal_vathu @ cardinal.words_to_digits)
                | (first_vathu @ cardinal.words_to_digits)
            )
            + pynutil.insert('"')
            + pynutil.insert(' morphosyntactic_features: "வது"')
        )
        graph_aam = (
            pynutil.insert('integer: "')
            + (
                (to_cardinal_aam @ cardinal.words_to_digits)
                | (first_aam @ cardinal.words_to_digits)
            )
            + pynutil.insert('"')
            + pynutil.insert(' morphosyntactic_features: "ஆம்"')
        )

        graph = (graph_vathu | graph_aam) + pynutil.insert(" preserve_order: true")
        self.fst = self.add_tokens(graph).optimize()
