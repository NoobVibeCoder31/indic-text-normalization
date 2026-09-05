"""
ITN verbalizer emitting written times.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    DIGIT,
    GraphFst,
    delete_preserve_order,
    delete_space,
)


def _two_digits() -> pynini.Fst:
    """
    Pad a one- or two-digit value to two digits.
    """
    return pynini.union(DIGIT + DIGIT, pynutil.insert("0") + DIGIT).optimize()


class TimeFst(GraphFst):
    """
    Finite state transducer for verbalizing times, e.g.
        time { hours: "10" minutes: "30" } -> 10:30
        time { hours: "10" } -> 10:00
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="time", kind="verbalize", deterministic=deterministic)

        hours = pynutil.delete('hours: "') + pynini.closure(DIGIT, 1, 2) + pynutil.delete('"')
        minutes = pynutil.delete('minutes: "') + _two_digits() + pynutil.delete('"')
        seconds = pynutil.delete('seconds: "') + _two_digits() + pynutil.delete('"')

        graph_h = hours + pynutil.insert(":00")
        graph_hm = hours + delete_space + pynutil.insert(":") + minutes
        graph_hms = graph_hm + delete_space + pynutil.insert(":") + seconds

        self.graph = (graph_hms | graph_hm | graph_h) + delete_preserve_order
        self.fst = self.delete_tokens(self.graph).optimize()
