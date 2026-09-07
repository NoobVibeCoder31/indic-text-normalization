"""
ITN verbalizer emitting written times.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import (
    DIGIT,
    NOT_QUOTE,
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
        time { hours: "10" suffix: "కు" } -> 10:00కు
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="time", kind="verbalize", deterministic=deterministic)

        valid_hour = pynini.union(
            DIGIT, "1" + DIGIT, "2" + pynini.union("0", "1", "2", "3")
        ).optimize()
        hours = pynutil.delete('hours: "') + valid_hour + pynutil.delete('"')
        # An hour above 23 is not a clock time: read it back as a number with its nouns.
        invalid_hour = pynini.difference(pynini.closure(DIGIT, 1), valid_hour)
        bad_hours = (
            pynutil.delete('hours: "')
            + invalid_hour
            + pynutil.delete('"')
            + pynutil.insert(" గంటల")
        )
        bad_minutes = (
            pynutil.delete('minutes: "')
            + pynini.closure(DIGIT, 1)
            + pynutil.delete('"')
            + pynutil.insert(" నిమిషాలు")
        )
        minutes = pynutil.delete('minutes: "') + _two_digits() + pynutil.delete('"')
        seconds = pynutil.delete('seconds: "') + _two_digits() + pynutil.delete('"')
        suffix = pynini.closure(
            delete_space
            + pynutil.delete('suffix: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"'),
            0,
            1,
        )

        graph_h = hours + pynutil.insert(":00")
        graph_hm = hours + delete_space + pynutil.insert(":") + minutes
        graph_hms = graph_hm + delete_space + pynutil.insert(":") + seconds
        graph_hs = hours + pynutil.insert(":00:") + delete_space + seconds
        graph_bad = bad_hours + pynini.closure(
            delete_space + pynutil.insert(" ") + bad_minutes, 0, 1
        )

        self.graph = (
            (graph_hms | graph_hm | graph_hs | graph_h | graph_bad) + suffix + delete_preserve_order
        )
        self.fst = self.delete_tokens(self.graph).optimize()
