"""
ITN tagger converting spoken Telugu dates to digit form.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import delete_space, DIGIT, GraphFst, insert_space
from indic_text_normalization.te.constants import LANG, TE_LETTER
from indic_text_normalization.te.itn.taggers.cardinal import CardinalFst


class DateFst(GraphFst):
    """
    Finite state transducer for classifying spoken dates, e.g.
        పదిహేను జూన్ రెండు వేల ఇరవై నాలుగు -> date { day: "15" month: "జూన్" year: "2024" }
        రెండు వేల ఇరవై నాలుగు జూన్ పదిహేను -> date { year: "2024" month: "జూన్" day: "15" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="date", kind="classify", deterministic=deterministic)

        # Month names are the output side of the TN months table.
        month_names = pynini.project(
            pynini.string_file(data_path(LANG, "date/months.tsv")), "output"
        ).optimize()

        # Days are 1-31 and years four digits, so రెండు వేల ఇరవై నాలుగు is never a day.
        valid_day = pynini.union(*[str(n) for n in range(1, 32)]).optimize()
        four_digits = DIGIT**4 + pynini.closure(TE_LETTER)
        day = (
            pynutil.insert('day: "') + (cardinal.words_to_digits @ valid_day) + pynutil.insert('"')
        )
        month = pynutil.insert('month: "') + month_names + pynutil.insert('"')
        # A case suffix on the year travels into the written form (… 2024లో).
        year_words = pynini.union(
            cardinal.words_to_digits, pynutil.add_weight(cardinal.words_to_digits_suffixed, 0.1)
        )
        year = pynutil.insert('year: "') + (year_words @ four_digits) + pynutil.insert('"')
        sep = delete_space + insert_space

        graph_dmy = day + sep + month + pynini.closure(sep + year, 0, 1)
        graph_my = month + sep + year
        graph_ymd = year + sep + month + sep + day
        graph_mdy = month + sep + day + sep + year

        graph = (graph_dmy | graph_my | graph_ymd | graph_mdy) + pynutil.insert(
            " preserve_order: true"
        )
        self.fst = self.add_tokens(graph).optimize()
