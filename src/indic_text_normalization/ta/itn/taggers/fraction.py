"""
ITN tagger converting spoken Tamil fractions to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import (
    delete_space,
    GraphFst,
    insert_space,
    sequential,
    SIGMA,
)
from indic_text_normalization.ta.constants import LANG
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class FractionFst(GraphFst):
    """
    Finite state transducer for classifying spoken fractions, e.g.
        நான்கில் மூன்று -> fraction { denominator: "4" numerator: "3" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="classify", deterministic=deterministic)

        denominator_il = pynini.string_file(data_path(LANG, "fraction/denominator_il.tsv"))
        # The regular locative, mirroring the TN fraction verbalizer: -இல் replaces the
        # final -உ, a ம்-final scale word takes -த்தில், and a hundreds compound -நூற்றில்.
        generic_il = SIGMA + pynini.union(
            pynini.cross("ில்", "ு"), pynini.cross("த்தில்", "ம்"), pynini.cross("ியில்", "ி")
        )
        hundreds_il = SIGMA + pynini.cross("நூற்றில்", "நூறு")
        denominator_words = sequential(
            (denominator_il | generic_il | hundreds_il) @ cardinal.words_to_digits
        )

        graph = (
            pynutil.insert('denominator: "')
            + denominator_words
            + pynutil.insert('"')
            + delete_space
            + insert_space
            + pynutil.insert('numerator: "')
            + cardinal.words_to_digits
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()
