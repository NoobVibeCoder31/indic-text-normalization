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

from indic_text_normalization.core.graph_utils import (
    delete_space,
    GraphFst,
    insert_space,
    NOT_QUOTE,
)
from indic_text_normalization.te.morphology import (
    NOT_ONE,
    ONE,
    optional_suffix_field,
    suffix_sandhi,
)

HOUR_ONE = "ఒంటి"


class TimeFst(GraphFst):
    """
    Finite state transducer for verbalizing time, e.g.
        time { hours: "పది" minutes: "ముప్పై" } -> పది గంటల ముప్పై నిమిషాలు
        time { hours: "పది" } -> పది గంటలు
        time { hours: "ఒంటి" } -> ఒంటి గంట
        time { hours: "పది" suffix: "కి" } -> పది గంటలకి
    """

    def __init__(self) -> None:
        super().__init__(name="time", kind="verbalize")

        not_one_hour = pynini.difference(pynini.closure(NOT_QUOTE, 1), pynini.accep(HOUR_ONE))

        def field(name: str, value: pynini.Fst) -> pynini.Fst:
            return pynutil.delete(f'{name}: "') + value + pynutil.delete('"')

        # ఒంటి గంట is invariant; other hours take గంటలు, or the oblique గంటల before minutes.
        hour_final = field(
            "hours", pynini.cross(HOUR_ONE, "ఒంటి గంట") | not_one_hour + pynutil.insert(" గంటలు")
        )
        hour_oblique = field(
            "hours", pynini.cross(HOUR_ONE, "ఒంటి గంట") | not_one_hour + pynutil.insert(" గంటల")
        )
        minute_final = field(
            "minutes", pynini.cross(ONE, "ఒక నిమిషం") | NOT_ONE + pynutil.insert(" నిమిషాలు")
        )
        minute_oblique = field(
            "minutes", pynini.cross(ONE, "ఒక నిమిషం") | NOT_ONE + pynutil.insert(" నిమిషాల")
        )
        second_final = field(
            "seconds", pynini.cross(ONE, "ఒక సెకను") | NOT_ONE + pynutil.insert(" సెకన్లు")
        )

        graph_h = hour_final
        graph_hm = hour_oblique + delete_space + insert_space + minute_final
        graph_hms = (
            hour_oblique
            + delete_space
            + insert_space
            + minute_oblique
            + delete_space
            + insert_space
            + second_final
        )
        graph_hs = hour_oblique + delete_space + insert_space + second_final

        meridiem = pynini.closure(
            pynutil.delete('meridiem: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
            + delete_space
            + insert_space,
            0,
            1,
        )
        graph = meridiem + (graph_hms | graph_hm | graph_hs | graph_h) + optional_suffix_field()
        self.graph = graph @ suffix_sandhi()
        self.fst = self.delete_tokens(self.graph).optimize()
