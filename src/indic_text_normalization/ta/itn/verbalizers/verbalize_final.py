"""
Sentence-level Tamil ITN verbalizer.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    GraphFst,
    delete_extra_space,
    delete_space,
)
from indic_text_normalization.ta.itn.verbalizers.verbalize import VerbalizeFst
from indic_text_normalization.ta.itn.verbalizers.word import WordFst


class VerbalizeFinalFst(GraphFst):
    """
    Finite state transducer that verbalizes an entire tagged ITN sentence, e.g.
    tokens { cardinal { integer: "23" } } tokens { name: "பேர்" } -> 23 பேர்
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize_final", kind="verbalize", deterministic=deterministic)

        types = (
            VerbalizeFst(deterministic=deterministic).fst | WordFst(deterministic=deterministic).fst
        )
        graph = (
            pynutil.delete("tokens")
            + delete_space
            + pynutil.delete("{")
            + delete_space
            + types
            + delete_space
            + pynutil.delete("}")
        )
        graph = delete_space + pynini.closure(graph + delete_extra_space) + graph + delete_space

        self.fst = graph.optimize()
