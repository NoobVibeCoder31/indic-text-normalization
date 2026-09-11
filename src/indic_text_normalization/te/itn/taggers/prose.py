"""
ITN tagger protecting number words that are ordinary words in prose.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.core.graph_utils import convert_space, GraphFst
from indic_text_normalization.te.constants import LANG


class ProseFst(GraphFst):
    """
    Finite state transducer keeping ambiguous number words as words, e.g.
        అంతా ఒకటి -> tokens { name: "అంతా ఒకటి" }

    Telugu needs no per-word condition beside these phrases: the number grammar never
    accepts bare ఒక, అర or పావు, so those read as nouns without help.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="prose", kind="classify", deterministic=deterministic)

        phrases = [row[0] for row in load_labels(data_path(LANG, "numbers/itn_prose_phrases.tsv"))]
        graph = convert_space(pynini.union(*phrases))
        self.fst = (pynutil.insert('name: "') + graph + pynutil.insert('"')).optimize()
