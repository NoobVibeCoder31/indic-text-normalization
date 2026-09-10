"""
ITN tagger converting spoken Tamil dates to digit form.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import delete_space, DIGIT, GraphFst
from indic_text_normalization.ta.constants import LANG, TA_LETTER
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class DateFst(GraphFst):
    """
    Finite state transducer for classifying spoken dates, e.g.
        பதினைந்து ஜூன் இரண்டு ஆயிரம் இருபத்துநான்கு
            -> date { day: "15" month: "ஜூன்" year: "2024" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="date", kind="classify", deterministic=deterministic)

        # Month names are the output side of the TN months table.
        month_names = pynini.project(
            pynini.string_file(data_path(LANG, "date/months.tsv")), "output"
        ).optimize()

        # A day is 1-31 and a year at most four digits. Range-binding them keeps the
        # tagger small and stops ஐந்நூறு ஜூன் reading as day 500.
        day_value = cardinal.words_to_digits @ pynini.union(*[str(d) for d in range(1, 32)])
        year_digits = pynini.closure(DIGIT, 1, 4)
        day = pynutil.insert('day: "') + day_value + pynutil.insert('"')
        month = pynutil.insert('month: "') + month_names + pynutil.insert('"')
        # A case suffix on the year is carried to the digits: ... இருபத்துநான்கில் -> 2024ல்.
        year_value = (cardinal.words_to_digits @ year_digits) | pynutil.add_weight(
            cardinal.suffixed_words_to_digits @ (year_digits + pynini.closure(TA_LETTER, 1)),
            0.05,
        )
        year = pynutil.insert('year: "') + year_value + pynutil.insert('"')

        graph_dmy = (
            day
            + delete_space
            + pynutil.insert(" ")
            + month
            + pynini.closure(delete_space + pynutil.insert(" ") + year, 0, 1)
        )
        graph_my = month + delete_space + pynutil.insert(" ") + year

        graph = (graph_dmy | graph_my) + pynutil.insert(" preserve_order: true")
        self.fst = self.add_tokens(graph).optimize()
