"""
ITN tagger protecting number words that are ordinary words in prose.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst, convert_space
from indic_text_normalization.core.utils import data_path, load_labels


class ProseFst(GraphFst):
    """
    Finite state transducer keeping ambiguous number phrases as words, e.g.
        అంతా ఒకటి -> tokens { name: "అంతా ఒకటి" }

    Reads ``numbers/itn_prose_phrases.tsv`` (phrase, reason) of ``lang``.
    """

    def __init__(self, lang: str, deterministic: bool = True) -> None:
        super().__init__(name="prose", kind="classify", deterministic=deterministic)

        phrases = [row[0] for row in load_labels(data_path(lang, "numbers/itn_prose_phrases.tsv"))]
        graph = convert_space(pynini.union(*phrases))
        self.fst = (pynutil.insert('name: "') + graph + pynutil.insert('"')).optimize()
