"""
ITN tagger converting spoken Tamil fractions to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst, delete_space, insert_space
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.utils import get_abs_path


class FractionFst(GraphFst):
    """
    Finite state transducer for classifying spoken fractions, e.g.
        நான்கில் மூன்று -> fraction { denominator: "4" numerator: "3" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="classify", deterministic=deterministic)

        denominator_il = pynini.string_file(get_abs_path("data/fraction/denominator_il.tsv"))
        denominator_words = (denominator_il @ cardinal.words_to_digits).optimize()

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
