import pynini
from pynini.examples import plurals
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import PUNCT_UNICODE, NOT_SPACE, SIGMA, GraphFst


class PunctuationFst(GraphFst):
    """
    Finite state transducer for classifying punctuation
        e.g. a, -> tokens { name: "a" } tokens { name: "," }

    Args:
        deterministic: if True will provide a single transduction option,
            for False multiple transductions are generated (used for audio-based normalization)
    """

    def __init__(self, deterministic: bool = True):
        super().__init__(name="punctuation", kind="classify", deterministic=deterministic)
        s = "!#%&'()*+,-./:;<=>?@^_`{|}~\""

        self.punct_marks = PUNCT_UNICODE + list(s)

        punct = pynini.union(*[pynini.escape(p) for p in self.punct_marks])
        punct = pynini.closure(punct, 1)

        # No "=" -> சமம் rewrite here: that is the TN direction. ITN must leave "=" alone.

        emphasis = (
            pynini.accep("<")
            + pynini.union(
                (
                    pynini.closure(NOT_SPACE - pynini.union("<", ">"), 1)
                    + pynini.closure(pynini.accep("/"), 0, 1)
                ),
                (pynini.accep("/") + pynini.closure(NOT_SPACE - pynini.union("<", ">"), 1)),
            )
            + pynini.accep(">")
        )
        punct = plurals._priority_union(emphasis, punct, SIGMA)

        self.graph = punct
        self.fst = (pynutil.insert('name: "') + self.graph + pynutil.insert('"')).optimize()
