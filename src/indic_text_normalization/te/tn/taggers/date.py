# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
# Copyright 2015 and onwards Google, Inc.
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

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import CHAR, DIGIT, GraphFst, insert_space
from indic_text_normalization.te.constants import (
    ASCII_TO_TE_DIGIT,
    ASCII_TO_TE_NUMBER,
    LANG,
    TE_DIGIT,
)
from indic_text_normalization.te.tn.taggers.cardinal import (
    CardinalFst,
    attach_case_suffix,
    ordinal_graph,
)

days = pynini.string_file(data_path(LANG, "date/days.tsv"))
months = pynini.string_file(data_path(LANG, "date/months.tsv"))
year_suffix = pynini.string_file(data_path(LANG, "date/year_suffix.tsv"))


class DateFst(GraphFst):
    """
    Finite state transducer for classifying date, e.g.
        "౦౧-౦౪-౨౦౨౪" -> date { day: "ఒకటి" month: "ఏప్రిల్" year: "రెండు వేల ఇరవై నాలుగు" }
        "15-06-1947" -> date { day: "పదిహేను" month: "జూన్" year: "పందొమ్మిది వందల నలభై ఏడు" }
        "2024-01-15" -> date { year: "రెండు వేల ఇరవై నాలుగు" month: "జనవరి" day: "పదిహేను" }

    Args:
        cardinal: cardinal GraphFst
    """

    def __init__(self, cardinal: CardinalFst) -> None:
        super().__init__(name="date", kind="classify")

        # Two-digit day/month in either script; a single digit is zero-padded.
        pad_zero = pynutil.insert("౦")
        two_digit_input = pynini.union(
            TE_DIGIT + TE_DIGIT,
            pad_zero + TE_DIGIT,
            pynini.compose(DIGIT + DIGIT, ASCII_TO_TE_NUMBER),
            pad_zero + pynini.compose(DIGIT, ASCII_TO_TE_DIGIT),
        ).optimize()
        days_graph = pynini.compose(two_digit_input, days).optimize()
        months_graph = pynini.compose(two_digit_input, months).optimize()

        # Four-digit years; 1100-1999 read as hundreds (పందొమ్మిది వందల నలభై ఏడు).
        year_core = pynini.union(
            pynutil.add_weight(cardinal.graph_year_hundreds, -0.05), cardinal.final_graph
        ).optimize()
        year_graph = pynini.union(
            pynini.compose(TE_DIGIT**4, year_core),
            pynini.compose(DIGIT**4, ASCII_TO_TE_NUMBER @ year_core),
        ).optimize()

        # Separators
        delete_separator = pynutil.delete(pynini.union("-", "/", "."))

        # One date uses one separator throughout. That is enforced by filtering the input
        # below rather than by building each ordering once per separator, which would
        # triple the tagger; without it 15-06.2024 and 2024/06-15 also tag as dates.
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

        day_component = pynutil.insert('day: "') + days_graph + pynutil.insert('"')
        month_component = pynutil.insert('month: "') + months_graph + pynutil.insert('"')
        # 2-digit years are rejected: 15-06-24 is too ambiguous with number ranges.
        # A case suffix on the date lands on the year (2024లో, 2024కి, 2024వ సంవత్సరం).
        year_component = (
            pynutil.insert('year: "')
            + (year_graph | attach_case_suffix(year_graph) | ordinal_graph(year_graph))
            + pynutil.insert('"')
        )

        graph_dd_mm_yyyy = (
            day_component
            + insert_space
            + delete_separator
            + month_component
            + insert_space
            + delete_separator
            + year_component
        )
        graph_mm_dd_yyyy = (
            month_component
            + insert_space
            + delete_separator
            + day_component
            + insert_space
            + delete_separator
            + year_component
            + pynutil.insert(" preserve_order: true")
        )
        graph_yyyy_mm_dd = (
            year_component
            + insert_space
            + delete_separator
            + month_component
            + insert_space
            + delete_separator
            + day_component
        )

        era_graph = pynutil.insert('era: "') + year_suffix + pynutil.insert('"')

        # Numeric dates require all three components with a 4-digit year; bare
        # MM-DD / MM-YY shapes are dropped so ranges like 10-20 stay cardinals.
        numeric_dates = pynini.compose(
            one_separator,
            pynutil.add_weight(graph_dd_mm_yyyy, -0.001)
            | pynutil.add_weight(graph_yyyy_mm_dd, -0.001)
            | graph_mm_dd_yyyy,
        )
        final_graph = numeric_dates | pynutil.add_weight(era_graph, -0.001)

        self.final_graph = final_graph.optimize()
        self.fst = self.add_tokens(self.final_graph)
