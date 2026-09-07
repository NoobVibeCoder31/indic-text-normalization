"""
ITN verbalizer emitting written ordinals.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import NOT_QUOTE, GraphFst


class OrdinalFst(GraphFst):
    """
    Finite state transducer for verbalizing ordinals, e.g.
        ordinal { integer: "5వ" } -> 5వ
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="verbalize", deterministic=deterministic)

        self.graph = (
            pynutil.delete('integer: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        self.fst = self.delete_tokens(self.graph).optimize()
