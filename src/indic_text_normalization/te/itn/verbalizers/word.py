"""
ITN verbalizer passing plain words through.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import CHAR, SIGMA, GraphFst, delete_space


class WordFst(GraphFst):
    """
    Finite state transducer for verbalizing plain words, e.g.
        tokens { name: "నమస్కారం" } -> నమస్కారం
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="word", kind="verbalize", deterministic=deterministic)

        # A value may itself be a U+0022 QUOTATION MARK token, so only the space is excluded.
        chars = pynini.closure(pynini.difference(CHAR, " "), 1)
        graph = pynutil.delete('name: "') + chars + pynutil.delete('"')
        # Multi-word values travel with U+00A0 NO-BREAK SPACE; write them with plain spaces.
        graph = graph @ pynini.cdrewrite(pynini.cross("\u00a0", " "), "", "", SIGMA)
        self.fst = (delete_space + graph + delete_space).optimize()
