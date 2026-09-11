"""
Word tagger shared by every language and both directions.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    ALPHA,
    MIN_NEG_WEIGHT,
    NOT_SPACE,
    GraphFst,
    convert_space,
)
from indic_text_normalization.core.punctuation import PunctuationFst

# Symbols a semiotic class owns, so the word class must not swallow them.
_CLASS_SYMBOLS = ["$", "€", "₩", "£", "¥", "#", "%"]


class WordFst(GraphFst):
    """
    Finite state transducer for classifying words, e.g.
        தமிழ் -> tokens { name: "தமிழ்" }

    Attributes
    ----------
    punctuation : ``PunctuationFst``
        Punctuation grammar whose marks bound a word.
    script : ``pynini.Fst``
        Acceptor for one character of the language's script block; a run of them is
        preferred over the fallback that accepts any non-space characters.
    pass_urls : ``bool``, optional (default = False)
        If True, a URL stays one token instead of splitting into punctuation marks.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        punctuation: PunctuationFst,
        *,
        script: pynini.Fst,
        pass_urls: bool = False,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="word", kind="classify", deterministic=deterministic)

        punct = punctuation.graph_input
        default_graph = pynini.closure(pynini.difference(NOT_SPACE, punct), 1)
        symbols_to_exclude = (pynini.union(*_CLASS_SYMBOLS) | punct).optimize()

        graph = pynini.closure(pynini.difference(script, symbols_to_exclude), 1)
        graph = pynutil.add_weight(graph, MIN_NEG_WEIGHT) | default_graph

        if pass_urls:
            url_body = pynini.closure(pynini.difference(NOT_SPACE, pynini.accep('"')), 1)
            url = (pynini.closure(ALPHA, 1) + "://" + url_body) | ("www." + url_body)
            graph = pynutil.add_weight(url, MIN_NEG_WEIGHT) | graph

        # No space is introduced around punctuation inside a word.
        graph = pynini.closure(graph + pynini.closure(punct + graph, 0, 1))

        self.graph = convert_space(graph)
        self.fst = (pynutil.insert('name: "') + self.graph + pynutil.insert('"')).optimize()
