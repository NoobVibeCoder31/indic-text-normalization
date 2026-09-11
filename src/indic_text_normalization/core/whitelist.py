"""
Whitelist (abbreviation and symbol) tagger shared by every language's TN grammar.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA, GraphFst, convert_space
from indic_text_normalization.core.utils import data_path, table_fst


class WhiteListFst(GraphFst):
    """
    Finite state transducer for classifying whitelist entries, e.g.
        டாக்டர். -> tokens { name: "டாக்டர்" }

    Attributes
    ----------
    lang : ``str``
        Language whose ``whitelist/abbreviations.tsv`` and ``whitelist/symbol.tsv`` are read.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(self, lang: str, deterministic: bool = True) -> None:
        super().__init__(name="whitelist", kind="classify", deterministic=deterministic)

        graph = table_fst(data_path(lang, "whitelist/abbreviations.tsv"))
        graph |= pynini.compose(
            pynini.difference(SIGMA, pynini.accep("/")).optimize(),
            table_fst(data_path(lang, "whitelist/symbol.tsv")),
        ).optimize()

        self.graph = convert_space(graph).optimize()
        self.fst = (pynutil.insert('name: "') + self.graph + pynutil.insert('"')).optimize()
