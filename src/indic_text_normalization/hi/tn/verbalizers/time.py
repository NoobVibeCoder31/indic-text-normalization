"""
Hindi TN time verbalizer.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    NOT_QUOTE,
    GraphFst,
    delete_space,
    insert_space,
)
from indic_text_normalization.core.tn_verbalizers import meridiem_by_hour
from indic_text_normalization.hi.constants import LANG

CLOCK = "बजे"  # a bare hour: दस बजे
HOUR_JOIN = "बजकर"  # an hour followed by minutes or seconds: दस बजकर तीस मिनट
MINUTE_NOUN = "मिनट"
SECOND_NOUN = "सेकंड"


class TimeFst(GraphFst):
    """
    Finite state transducer for verbalizing time, e.g.
        time { hours: "दस" minutes: "तीस" } -> दस बजकर तीस मिनट
        time { hours: "दस" } -> दस बजे
        time { hours: "दस" minutes: "तीस" seconds: "पैंतालीस" } -> दस बजकर तीस मिनट पैंतालीस सेकंड
        time { hours: "दस" minutes: "तीस" meridiem: "AM" } -> सुबह दस बजकर तीस मिनट
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="time", kind="verbalize", deterministic=deterministic)

        any_word = pynini.closure(NOT_QUOTE, 1)

        def field(name: str, noun: str) -> pynini.Fst:
            return (
                pynutil.delete(f'{name}: "')
                + any_word
                + pynutil.delete('"')
                + pynutil.insert(f" {noun}")
            )

        day_part = (
            pynutil.delete('meridiem: "')
            + pynini.difference(any_word, pynini.union("AM", "PM"))
            + pynutil.delete('"')
            + delete_space
            + insert_space
        )
        optional_day_part = pynini.closure(day_part, 0, 1)
        minutes = field("minutes", MINUTE_NOUN)
        seconds = field("seconds", SECOND_NOUN)
        rest = (
            delete_space
            + insert_space
            + minutes
            + pynini.closure(delete_space + insert_space + seconds, 0, 1)
            | delete_space + insert_space + seconds
        )

        bare = pynini.union(
            optional_day_part + field("hours", CLOCK), meridiem_by_hour(LANG, CLOCK)
        )
        joined = pynini.union(
            optional_day_part + field("hours", HOUR_JOIN), meridiem_by_hour(LANG, HOUR_JOIN)
        )
        graph = bare | joined + rest
        self.fst = self.delete_tokens(graph).optimize()
