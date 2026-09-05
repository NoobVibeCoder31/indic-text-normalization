# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
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

from indic_text_normalization.ta.constants import (
    ASCII_TO_TA_DIGIT,
    DIGIT,
    SPACE,
    TA_DIGIT,
    TA_NON_ZERO,
    TA_ZERO,
    GraphFst,
    insert_space,
)
from indic_text_normalization.ta.utils import get_abs_path

ascii_to_tamil_number = pynini.closure(ASCII_TO_TA_DIGIT).optimize()

hours_graph = pynini.string_file(get_abs_path("data/time/hours.tsv"))
minutes_graph = pynini.string_file(get_abs_path("data/time/minutes.tsv"))
seconds_graph = pynini.string_file(get_abs_path("data/time/seconds.tsv"))


class TimeFst(GraphFst):
    """
    Finite state transducer for classifying time, e.g.
        ௧௨:௩௦:௩௦ -> time { hours: "பன்னிரண்டு" minutes: "முப்பது" seconds: "முப்பது" }
        1:40 -> time { hours: "ஒன்று" minutes: "நாற்பது" }
        ௧:௦௦ -> time { hours: "ஒன்று" }
    """

    def __init__(self) -> None:
        super().__init__(name="time", kind="classify")

        delete_colon = pynutil.delete(":")

        delete_leading_zero_tamil = (
            (TA_NON_ZERO + TA_DIGIT) | (pynutil.delete(TA_ZERO) + TA_DIGIT) | TA_DIGIT
        ).optimize()
        delete_leading_zero_ascii = (
            (pynini.difference(DIGIT, "0") + DIGIT) | (pynutil.delete("0") + DIGIT) | DIGIT
        ).optimize()

        hour_input = (
            pynini.compose(delete_leading_zero_tamil, hours_graph)
            | pynini.compose(delete_leading_zero_ascii, ascii_to_tamil_number @ hours_graph)
        ).optimize()
        minute_input = (
            pynini.compose(pynini.closure(TA_DIGIT, 1), minutes_graph)
            | pynini.compose(pynini.closure(DIGIT, 1), ascii_to_tamil_number @ minutes_graph)
        ).optimize()
        second_input = (
            pynini.compose(pynini.closure(TA_DIGIT, 1), seconds_graph)
            | pynini.compose(pynini.closure(DIGIT, 1), ascii_to_tamil_number @ seconds_graph)
        ).optimize()

        self.hours = pynutil.insert('hours: "') + hour_input + pynutil.insert('" ')
        self.minutes = pynutil.insert('minutes: "') + minute_input + pynutil.insert('" ')
        self.seconds = pynutil.insert('seconds: "') + second_input + pynutil.insert('" ')

        # The verbalizer inserts மணி itself, so a trailing written மணிக்கு is absorbed here.
        optional_manikku = pynini.closure(
            pynini.closure(SPACE, 0, 1) + pynutil.delete("மணிக்கு"), 0, 1
        ).optimize()

        graph_hms = (
            self.hours
            + delete_colon
            + insert_space
            + self.minutes
            + delete_colon
            + insert_space
            + self.seconds
            + optional_manikku
        )
        graph_hm = self.hours + delete_colon + insert_space + self.minutes + optional_manikku
        graph_h = (
            self.hours
            + delete_colon
            + (pynutil.delete("௦௦") | pynutil.delete("00"))
            + optional_manikku
        )

        final_graph = (
            graph_hms | pynutil.add_weight(graph_hm, 1.0) | pynutil.add_weight(graph_h, 0.8)
        )

        self.fst = self.add_tokens(final_graph).optimize()
