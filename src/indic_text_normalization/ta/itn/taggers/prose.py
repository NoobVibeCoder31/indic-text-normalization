"""
ITN tagger protecting number words that are ordinary words in prose.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.ta.itn.ambiguity import STANDALONE, ambiguous_words
from indic_text_normalization.core.graph_utils import convert_space, GraphFst
from indic_text_normalization.ta.constants import LANG, TA_LETTER


class ProseFst(GraphFst):
    """
    Finite state transducer keeping ambiguous number words as words, e.g.
        கால் வலிக்கிறது -> tokens { name: "கால் வலிக்கிறது" }
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="prose", kind="classify", deterministic=deterministic)

        phrases = [row[0] for row in load_labels(data_path(LANG, "numbers/itn_prose_phrases.tsv"))]
        ambiguous = [word for word, _ in ambiguous_words(STANDALONE)]

        # An ambiguous word reads as a fraction only on its own; any Tamil word after it
        # (கால் வலிக்கிறது, அரை நிஜார்) makes the word reading the right one.
        tamil_word = pynini.closure(TA_LETTER, 1)
        followed = pynini.union(*ambiguous) + pynini.accep(" ") + tamil_word

        graph = convert_space(pynini.union(*phrases) | followed)
        self.fst = (pynutil.insert('name: "') + graph + pynutil.insert('"')).optimize()
