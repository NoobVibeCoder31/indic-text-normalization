"""
ITN tagger converting spoken Telugu fractions to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    delete_space,
    GraphFst,
    insert_space,
    sequential,
)
from indic_text_normalization.te.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.te.tn.verbalizers.fraction import DENOMINATOR_INTA


class FractionFst(GraphFst):
    """
    Finite state transducer for classifying spoken fractions, e.g.
        నాలుగింట మూడు వంతులు -> fraction { denominator: "4" numerator: "3" }
        మూడు బై నాలుగు -> fraction { numerator: "3" denominator: "4" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="classify", deterministic=deterministic)

        # Undo the oblique -ింట on the denominator, then read it as a number.
        denominator_words = sequential(pynini.invert(DENOMINATOR_INTA) @ cardinal.words_to_digits)
        vanthu = pynini.union("వంతులు", "వంతుల", "వంతు", "భాగాలు", "భాగం")
        numerator_words = pynini.union(cardinal.words_to_digits, pynini.cross("ఒక", "1"))

        denominator = pynutil.insert('denominator: "') + denominator_words + pynutil.insert('"')
        numerator = pynutil.insert('numerator: "') + numerator_words + pynutil.insert('"')

        graph = (
            denominator
            + delete_space
            + insert_space
            + numerator
            + pynini.closure(delete_space + pynutil.delete(vanthu), 0, 1)
        )
        # Mixed number: రెండు మరియు నాలుగింట మూడు వంతులు -> 2 3/4.
        integer = (
            pynutil.insert('integer_part: "')
            + cardinal.words_to_digits
            + pynutil.insert('"')
            + delete_space
            + pynutil.delete("మరియు")
            + delete_space
            + insert_space
        )
        graph = pynini.closure(integer, 0, 1) + graph
        # Spoken "బై" form: మూడు బై నాలుగు -> 3/4.
        graph |= (
            pynutil.insert('numerator: "')
            + cardinal.words_to_digits
            + pynutil.insert('"')
            + delete_space
            + pynutil.delete("బై")
            + delete_space
            + insert_space
            + pynutil.insert('denominator: "')
            + cardinal.words_to_digits
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()
