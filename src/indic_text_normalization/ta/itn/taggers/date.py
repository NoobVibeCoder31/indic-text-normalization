"""
ITN tagger converting spoken Tamil dates to digit form.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst, delete_space
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.utils import get_abs_path


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
            pynini.string_file(get_abs_path("data/date/months.tsv")), "output"
        ).optimize()

        day = pynutil.insert('day: "') + cardinal.words_to_digits + pynutil.insert('"')
        month = pynutil.insert('month: "') + month_names + pynutil.insert('"')
        year = pynutil.insert('year: "') + cardinal.words_to_digits + pynutil.insert('"')

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
