"""
Punctuation tagger shared by every language and both directions.
"""

import pynini
from pynini.examples import plurals
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    NOT_SPACE,
    SIGMA,
    GraphFst,
    punctuation_code_points,
)
from indic_text_normalization.core.utils import data_path

# ASCII marks that Unicode does not categorise as punctuation.
_ASCII_MARKS = "!#%&'()*+,-./:;<=>?@^_`{|}~\""


class PunctuationFst(GraphFst):
    """
    Finite state transducer for classifying punctuation, e.g.
        a, -> tokens { name: "a" } tokens { name: "," }

    Attributes
    ----------
    lang : ``str``
        Language whose ``math_operations.tsv`` spells the equals sign.
    speak_equals : ``bool``, optional (default = False)
        If True, U+003D EQUALS SIGN is rewritten to its spoken word. Only TN wants this;
        ITN must leave it unchanged, as nothing in that direction recovers it.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self, lang: str, *, speak_equals: bool = False, deterministic: bool = True
    ) -> None:
        super().__init__(name="punctuation", kind="classify", deterministic=deterministic)

        self.punct_marks = punctuation_code_points() + list(_ASCII_MARKS)
        punct = pynini.closure(pynini.union(*[pynini.escape(p) for p in self.punct_marks]), 1)

        if speak_equals:
            math_operations = pynini.string_file(data_path(lang, "math_operations.tsv"))
            punct = plurals._priority_union(pynini.union("=") @ math_operations, punct, SIGMA)

        # Markup such as <b> or </b> stays one token instead of splitting into marks.
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
        # pynini.Fst.project mutates in place, so the word tagger takes this pre-projected
        # copy rather than projecting the graph the tokenizer also holds.
        self.graph_input = punct.copy().project("input").optimize()
        self.fst = (pynutil.insert('name: "') + self.graph + pynutil.insert('"')).optimize()
