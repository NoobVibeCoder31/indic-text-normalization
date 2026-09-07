"""
ITN verbalizer passing plain words through.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import CHAR, GraphFst, delete_space

# Values may contain non-breaking spaces inserted by convert_space.
_NOT_QUOTE = pynini.difference(CHAR, r'"').optimize()


class WordFst(GraphFst):
    """
    Finite state transducer for verbalizing plain words, e.g.
        tokens { name: "నమస్కారం" } -> నమస్కారం
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="word", kind="verbalize", deterministic=deterministic)

        graph = pynutil.delete('name: "') + pynini.closure(_NOT_QUOTE, 1) + pynutil.delete('"')
        self.fst = (delete_space + graph + delete_space).optimize()
