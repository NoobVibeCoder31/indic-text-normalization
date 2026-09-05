"""
ITN tagger converting spoken Tamil numbers to ASCII digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    CHAR,
    DIGIT,
    TA_TO_ASCII_DIGIT,
    GraphFst,
)
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst as TnCardinalFst
from indic_text_normalization.ta.utils import get_abs_path


class CardinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken cardinals, e.g.
        இருபத்துமூன்று -> cardinal { integer: "23" }
        மைனஸ் நூற்று இருபது -> cardinal { negative: "true" integer: "120" }
    """

    def __init__(self, tn_cardinal: TnCardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="cardinal", kind="classify", deterministic=deterministic)

        # Every written form the TN grammar accepts, inverted and filtered to ASCII digits.
        # The TN grammar emits a leading space before நூற்று forms, so allow inserting one.
        to_ascii = pynini.closure(pynini.union(TA_TO_ASCII_DIGIT, DIGIT))
        optional_leading_space = pynini.closure(pynutil.insert(" "), 0, 1) + pynini.closure(CHAR)
        inverted = (
            optional_leading_space @ pynini.invert(tn_cardinal.final_graph) @ to_ascii
        ).optimize()

        # Spoken variants with spaced compounds, adapted from indic-num2words.
        variants = pynini.string_file(get_abs_path("data/numbers/itn_variants.tsv")).optimize()

        self.words_to_digits = pynini.union(inverted, variants).optimize()

        optional_minus = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("மைனஸ் ", '"true" '), 0, 1
        )

        graph = (
            optional_minus
            + pynutil.insert('integer: "')
            + self.words_to_digits
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()
