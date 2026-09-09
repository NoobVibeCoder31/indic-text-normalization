"""
ITN verbalizer emitting written dates.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
    insert_space,
)


class DateFst(GraphFst):
    """
    Finite state transducer for verbalizing dates, e.g.
        date { day: "15" month: "ஜூன்" year: "2024" } -> 15 ஜூன் 2024
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="date", kind="verbalize", deterministic=deterministic)

        day = pynutil.delete('day: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        month = pynutil.delete('month: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        year = pynutil.delete('year: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')

        graph_dmy = (
            day
            + delete_space
            + insert_space
            + month
            + pynini.closure(delete_space + insert_space + year, 0, 1)
        )
        graph_my = month + delete_space + insert_space + year

        self.graph = (graph_dmy | graph_my) + delete_preserve_order
        self.fst = self.delete_tokens(self.graph).optimize()
