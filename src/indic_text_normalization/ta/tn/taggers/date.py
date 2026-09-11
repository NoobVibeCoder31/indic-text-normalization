# Copyright (c) 2024, NVIDIA CORPORATION & AFFILIATES.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import CHAR, DIGIT, GraphFst, insert_space
from indic_text_normalization.ta.constants import LANG, TA_DIGIT
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst

# Convert Arabic digits (0-9) to Tamil digits (௦-௯)
arabic_to_tamil_digit = pynini.string_map(
    [
        ("0", "௦"),
        ("1", "௧"),
        ("2", "௨"),
        ("3", "௩"),
        ("4", "௪"),
        ("5", "௫"),
        ("6", "௬"),
        ("7", "௭"),
        ("8", "௮"),
        ("9", "௯"),
    ]
).optimize()
arabic_to_tamil_number = pynini.closure(arabic_to_tamil_digit).optimize()

days = pynini.string_file(data_path(LANG, "date/days.tsv"))
months = pynini.string_file(data_path(LANG, "date/months.tsv"))
year_suffix = pynini.string_file(data_path(LANG, "date/year_suffix.tsv"))


class DateFst(GraphFst):
    """
    Finite state transducer for classifying date, e.g.
        "௦௧-௦௪-௨௦௨௪" -> date { day: "ஒன்று" month: "ஏப்ரல்" year: "இரண்டாயிரத்து இருபத்துநான்கு" }
        "01-04-2024" -> date { day: "ஒன்று" month: "ஏப்ரல்" year: "இரண்டாயிரத்து இருபத்துநான்கு" }
        "2024-01-15" -> date { year: "இரண்டாயிரத்து இருபத்துநான்கு" month: "ஜனவரி" day: "பதினைந்து" }

    Args:
        cardinal: cardinal GraphFst
        deterministic: if True will provide a single transduction option,
            for False multiple transduction are generated (used for audio-based normalization)
    """

    def __init__(self, cardinal: CardinalFst) -> None:
        super().__init__(name="date", kind="classify")

        cardinal_graph = cardinal.final_graph

        # Support both Tamil and Arabic digits for days
        # Tamil digits path: Tamil digits -> days mapping
        pad_zero = pynutil.insert("\u0be6")
        tamil_day_input = (TA_DIGIT + TA_DIGIT) | (pad_zero + TA_DIGIT)
        tamil_days_graph = pynini.compose(tamil_day_input, days).optimize()

        # Arabic digits path: Arabic digits -> convert to Tamil -> days mapping
        arabic_day_input = pynini.compose(DIGIT + DIGIT, arabic_to_tamil_number) | (
            pad_zero + pynini.compose(DIGIT, arabic_to_tamil_number)
        )
        arabic_days_graph = pynini.compose(arabic_day_input, days).optimize()

        days_graph = tamil_days_graph | arabic_days_graph

        # Support both Tamil and Arabic digits for months
        tamil_month_input = (TA_DIGIT + TA_DIGIT) | (pad_zero + TA_DIGIT)
        tamil_months_graph = pynini.compose(tamil_month_input, months).optimize()

        arabic_month_input = pynini.compose(DIGIT + DIGIT, arabic_to_tamil_number) | (
            pad_zero + pynini.compose(DIGIT, arabic_to_tamil_number)
        )
        arabic_months_graph = pynini.compose(arabic_month_input, months).optimize()

        months_graph = tamil_months_graph | arabic_months_graph

        # Year graph - support both Tamil and Arabic 4-digit years
        tamil_year_input = TA_DIGIT + TA_DIGIT + TA_DIGIT + TA_DIGIT
        tamil_year_graph = pynini.compose(tamil_year_input, cardinal_graph).optimize()

        arabic_year_input = DIGIT + DIGIT + DIGIT + DIGIT
        arabic_year_graph = pynini.compose(
            arabic_year_input, arabic_to_tamil_number @ cardinal_graph
        ).optimize()

        year_graph = tamil_year_graph | arabic_year_graph

        # Separators
        delete_separator = pynutil.delete(pynini.union("-", "/", "."))

        # One date uses one separator throughout. That is enforced by filtering the input
        # below rather than by building each ordering once per separator, which would
        # triple the tagger; without it 15-06/2024 and 2024/06-15 also tag as dates.
        not_separator = pynini.difference(CHAR, pynini.union("-", "/", "."))
        one_separator = pynini.union(
            *[
                pynini.closure(not_separator)
                + separator
                + pynini.closure(not_separator)
                + separator
                + pynini.closure(not_separator)
                for separator in ("-", "/", ".")
            ]
        ).optimize()

        # Build date components with labels
        day_component = pynutil.insert('day: "') + days_graph + pynutil.insert('"')
        month_component = pynutil.insert('month: "') + months_graph + pynutil.insert('"')
        # 2-digit years are rejected: 15-06-24 is too ambiguous with number ranges.
        # A case suffix on the date lands on the year: 2024ல் -> ...நான்கில்.
        year_locative = (
            year_graph
            @ (
                pynini.closure(CHAR)
                + pynini.union(pynini.cross("ு", "ில்"), pynini.cross("ம்", "த்தில்"))
            )
        ) + pynutil.delete(pynini.union("ல்", "இல்"))
        year_dative = year_graph + pynini.union(
            pynini.accep("க்கு"), pynini.accep("க்குள்"), pynini.accep("க்கும்")
        )
        # 2024ஆம் (தேதி/ஆண்டு): the ordinal stem replaces the final vowel.
        year_aam = (
            year_graph
            @ (
                pynini.closure(CHAR)
                + pynini.union(pynini.cross("ு", "ா"), pynini.cross("ம்", "மா"))
            )
        ) + pynini.cross("ஆம்", "ம்")
        year_component = (
            pynutil.insert('year: "')
            + (year_graph | year_locative | year_dative | year_aam)
            + pynutil.insert('"')
        )

        def joined(first: pynini.Fst, second: pynini.Fst, third: pynini.Fst) -> pynini.Fst:
            """
            Join three date components with a separator between each pair.
            """
            return (
                first
                + insert_space
                + delete_separator
                + second
                + insert_space
                + delete_separator
                + third
            )

        # DD-MM-YYYY format (common in India)
        graph_dd_mm_yyyy = joined(day_component, month_component, year_component)

        # MM-DD-YYYY format
        graph_mm_dd_yyyy = joined(month_component, day_component, year_component) + pynutil.insert(
            " preserve_order: true"
        )

        # YYYY-MM-DD format (ISO format)
        graph_yyyy_mm_dd = joined(year_component, month_component, day_component)

        # Year suffix (A.D., B.C., etc.)
        era_graph = pynutil.insert('era: "') + year_suffix + pynutil.insert('"')

        # Numeric dates require all three components with a 4-digit year; bare
        # MM-DD / MM-YY shapes are dropped so ranges like 10-20 stay cardinals.
        numeric_dates = pynini.compose(
            one_separator,
            pynutil.add_weight(graph_dd_mm_yyyy, -0.001)  # Prefer DD-MM-YYYY
            | pynutil.add_weight(graph_yyyy_mm_dd, -0.001)  # ISO format
            | graph_mm_dd_yyyy,
        )
        final_graph = numeric_dates | pynutil.add_weight(era_graph, -0.001)

        self.final_graph = final_graph.optimize()
        self.fst = self.add_tokens(self.final_graph)
