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

from indic_text_normalization.te.constants import (
    ASCII_TO_TE_NUMBER,
    CASE_SUFFIXES,
    DIGIT,
    SPACE,
    TE_DIGIT,
    TE_NON_ZERO,
    TE_ZERO,
    GraphFst,
    insert_space,
)
from indic_text_normalization.te.utils import get_abs_path

hours_graph = pynini.string_file(get_abs_path("data/time/hours.tsv"))
minutes_graph = pynini.string_file(get_abs_path("data/time/minutes.tsv"))
seconds_graph = pynini.string_file(get_abs_path("data/time/seconds.tsv"))

# Day-part words that make a press-style dotted time (ఉదయం 10.30) a clock reading.
DAY_PARTS = [
    "ఉదయం",
    "ఉదయాన్నే",
    "తెల్లవారుజామున",
    "మధ్యాహ్నం",
    "సాయంత్రం",
    "రాత్రి",
    "పూర్వాహ్నం",
    "అపరాహ్నం",
]
DAY_PART_ABBREVIATIONS = {
    "ఉ.": "ఉదయం",
    "సా.": "సాయంత్రం",
    "మ.": "మధ్యాహ్నం",
    "రా.": "రాత్రి",
}


class TimeFst(GraphFst):
    """
    Finite state transducer for classifying time, e.g.
        ౧౨:౩౦:౩౦ -> time { hours: "పన్నెండు" minutes: "ముప్పై" seconds: "ముప్పై" }
        1:40 -> time { hours: "ఒంటి" minutes: "నలభై" }
        10:00కి -> time { hours: "పది" suffix: "కి" }
    """

    def __init__(self) -> None:
        super().__init__(name="time", kind="classify")

        delete_colon = pynutil.delete(":")

        delete_leading_zero_te = (
            (TE_NON_ZERO + TE_DIGIT) | (pynutil.delete(TE_ZERO) + TE_DIGIT) | TE_DIGIT
        ).optimize()
        delete_leading_zero_ascii = (
            (pynini.difference(DIGIT, "0") + DIGIT) | (pynutil.delete("0") + DIGIT) | DIGIT
        ).optimize()

        hour_input = (
            pynini.compose(delete_leading_zero_te, hours_graph)
            | pynini.compose(delete_leading_zero_ascii, ASCII_TO_TE_NUMBER @ hours_graph)
        ).optimize()
        minute_input = (
            pynini.compose(pynini.closure(TE_DIGIT, 1), minutes_graph)
            | pynini.compose(pynini.closure(DIGIT, 1), ASCII_TO_TE_NUMBER @ minutes_graph)
        ).optimize()
        second_input = (
            pynini.compose(pynini.closure(TE_DIGIT, 1), seconds_graph)
            | pynini.compose(pynini.closure(DIGIT, 1), ASCII_TO_TE_NUMBER @ seconds_graph)
        ).optimize()

        self.hours = pynutil.insert('hours: "') + hour_input + pynutil.insert('" ')
        self.minutes = pynutil.insert('minutes: "') + minute_input + pynutil.insert('" ')
        self.seconds = pynutil.insert('seconds: "') + second_input + pynutil.insert('" ')

        # The verbalizer inserts గంటలు itself, so a trailing written గంటలు/గంటలకు (and a
        # bare case suffix on the digits: 3:30కి) is absorbed; a dative/locative on the
        # time travels as a suffix field attached to the last time noun.
        space = pynini.closure(SPACE, 0, 1)
        bare_suffix = pynini.union(*CASE_SUFFIXES, "లోపు")
        hour_word_suffix = pynini.union(
            pynini.cross("గంటలకు", "కు"),
            pynini.cross("గంటలకి", "కి"),
            pynini.cross("గంటలకే", "కే"),
            pynini.cross("గంటలలో", "లో"),
            pynini.cross("గంటలలోపు", "లోపు"),
            pynini.cross("గంటలవరకు", "వరకు"),
            pynini.cross("గంటల వరకు", "వరకు"),
            pynini.cross("గంటకు", "కు"),
            pynini.cross("గంటకి", "కి"),
        )
        bare_suffix_field = pynutil.insert('suffix: "') + bare_suffix + pynutil.insert('" ')
        hour_word_field = pynutil.insert('suffix: "') + hour_word_suffix + pynutil.insert('" ')
        delete_hour_word = pynutil.delete(pynini.union("గంటలు", "గంటల", "గంట", "గం.", "గం"))
        # A bare suffix must be glued to the digits; an hour word may follow a space.
        hour_word_tail = space + (delete_hour_word | hour_word_field)
        optional_tail = pynini.closure(hour_word_tail | bare_suffix_field, 0, 1).optimize()

        graph_hms = (
            self.hours
            + delete_colon
            + insert_space
            + self.minutes
            + delete_colon
            + insert_space
            + self.seconds
            + optional_tail
        )
        delete_zero_seconds = pynini.closure(pynutil.delete(pynini.union(":00", ":౦౦")), 0, 1)
        graph_hm = (
            self.hours
            + delete_colon
            + insert_space
            + self.minutes
            + delete_zero_seconds
            + optional_tail
        )
        delete_zero_minutes = delete_colon + (pynutil.delete("౦౦") | pynutil.delete("00"))
        graph_h = self.hours + delete_zero_minutes + delete_zero_seconds + optional_tail
        # 10:00:30 keeps only the seconds: పది గంటల ముప్పై సెకన్లు.
        graph_h_s = (
            self.hours
            + delete_zero_minutes
            + delete_colon
            + insert_space
            + self.seconds
            + optional_tail
        )

        # Trailing AM/PM becomes a meridiem word the verbalizer fronts.
        meridiem = pynini.closure(
            pynutil.delete(pynini.closure(" ", 0, 1))
            + pynutil.insert('meridiem: "')
            + (
                pynini.cross(pynini.union("AM", "am", "A.M.", "a.m."), "పూర్వాహ్నం")
                | pynini.cross(pynini.union("PM", "pm", "P.M.", "p.m."), "అపరాహ్నం")
            )
            + pynutil.insert('" '),
            0,
            1,
        )

        final_graph = (
            graph_hms
            | pynutil.add_weight(graph_hm, 1.0)
            | pynutil.add_weight(graph_h_s, 1.0)
            | pynutil.add_weight(graph_h, 0.8)
        ) + meridiem

        # A bare hour with AM/PM is a clock time: 7 AM, 7pm.
        required_meridiem = (
            pynutil.delete(pynini.closure(" ", 0, 1))
            + pynutil.insert('meridiem: "')
            + (
                pynini.cross(pynini.union("AM", "am", "A.M.", "a.m."), "పూర్వాహ్నం")
                | pynini.cross(pynini.union("PM", "pm", "P.M.", "p.m."), "అపరాహ్నం")
            )
            + pynutil.insert('" ')
        )
        final_graph |= pynutil.add_weight(self.hours + required_meridiem, 0.9)

        # Press-style dotted time (10.30) is only a time with a clock context: a trailing
        # గంటలు/గంటలకు, or a day-part word / ఉ. / సా. before or after it.
        two_digit_minutes = pynini.compose(
            pynini.union(TE_DIGIT + TE_DIGIT, DIGIT + DIGIT), minute_input
        )
        dotted = (
            self.hours
            + pynutil.delete(".")
            + insert_space
            + pynutil.insert('minutes: "')
            + two_digit_minutes
            + pynutil.insert('" ')
        )
        # 6.00 reads as the bare hour.
        dotted |= self.hours + pynutil.delete(pynini.union(".00", ".౦౦"))
        trailing_hour_word = hour_word_tail
        # With a day-part word the time may also carry a glued suffix (ఉదయం 10.30కి).
        dotted_tail = pynini.closure(hour_word_tail | bare_suffix_field, 0, 1)
        contexts = [(w, w) for w in DAY_PARTS] + list(DAY_PART_ABBREVIATIONS.items())
        dotted_graphs = [dotted + trailing_hour_word, dotted + dotted_tail + required_meridiem]
        for written, spoken in contexts:
            meridiem_field = pynutil.insert(f'meridiem: "{spoken}" ')
            dotted_graphs.append(
                pynutil.delete(written)
                + pynutil.delete(" ")
                + dotted
                + dotted_tail
                + meridiem_field
            )
            dotted_graphs.append(dotted + space + pynutil.delete(written) + meridiem_field)
        # A cued dotted time must outrank a measure reading of the same span (10.30 గం.)
        # ... even when the cue is the unit-like గం. followed by sentence punctuation.
        final_graph |= pynutil.add_weight(pynini.union(*dotted_graphs), -2.5)

        self.fst = self.add_tokens(final_graph).optimize()
