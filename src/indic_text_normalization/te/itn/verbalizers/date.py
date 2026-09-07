"""
ITN verbalizer emitting written dates.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import (
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
    insert_space,
)


class DateFst(GraphFst):
    """
    Finite state transducer for verbalizing dates, e.g.
        date { day: "15" month: "జూన్" year: "2024" } -> 15 జూన్ 2024
        date { year: "2024" month: "జూన్" day: "15" } -> 2024 జూన్ 15
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="date", kind="verbalize", deterministic=deterministic)

        day = pynutil.delete('day: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        month = pynutil.delete('month: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        year = pynutil.delete('year: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        sep = delete_space + insert_space

        graph_dmy = day + sep + month + pynini.closure(sep + year, 0, 1)
        graph_my = month + sep + year
        graph_ymd = year + sep + month + sep + day
        graph_mdy = month + sep + day + sep + year

        self.graph = (graph_dmy | graph_my | graph_ymd | graph_mdy) + delete_preserve_order
        self.fst = self.delete_tokens(self.graph).optimize()
