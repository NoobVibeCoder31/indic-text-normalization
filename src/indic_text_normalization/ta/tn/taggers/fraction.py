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

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst
from indic_text_normalization.ta.constants import TA_DIGIT
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst

# Vulgar fraction signs as (sign, numerator word, denominator word).
VULGAR_FRACTIONS = [
    ("½", "ஒன்று", "இரண்டு"),
    ("¼", "ஒன்று", "நான்கு"),
    ("¾", "மூன்று", "நான்கு"),
]


class FractionFst(GraphFst):
    """
    Finite state transducer for classifying fractions, e.g.
        3/4 -> fraction { numerator: "மூன்று" denominator: "நான்கு" }
        ½ -> fraction { numerator: "ஒன்று" denominator: "இரண்டு" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="classify", deterministic=deterministic)

        cardinal_graph = cardinal.final_graph

        # A zero or zero-led denominator (1/0, 15/06) has no locative form.
        any_digit = pynini.union(DIGIT, TA_DIGIT)
        non_zero_led = pynini.difference(
            pynini.closure(any_digit, 1),
            pynini.union("0", "௦") + pynini.closure(any_digit),
        ).optimize()
        denominator_graph = pynini.compose(non_zero_led, cardinal_graph).optimize()

        integer = pynutil.insert('integer_part: "') + cardinal_graph + pynutil.insert('"')
        # A zero-led numerator (06/24) is a date fragment, not a fraction.
        numerator_input = pynini.difference(
            pynini.closure(any_digit, 1),
            pynini.union("0", "௦") + pynini.closure(any_digit, 1),
        ).optimize()
        numerator = (
            pynutil.insert('numerator: "')
            + pynini.compose(numerator_input, cardinal_graph)
            + (pynini.cross("/", '" ') | pynini.cross(" / ", '" '))
        )
        denominator = pynutil.insert('denominator: "') + denominator_graph + pynutil.insert('"')

        graph = pynini.closure(integer + pynini.accep(" "), 0, 1) + (numerator + denominator)
        optional_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" '), 0, 1
        )
        graph = optional_negative + graph

        vulgar = pynini.union(
            *[
                pynutil.delete(sign) + pynutil.insert(f'numerator: "{num}" denominator: "{den}"')
                for sign, num, den in VULGAR_FRACTIONS
            ]
        )
        optional_space = pynini.closure(pynini.accep(" "), 0, 1)
        graph |= pynini.closure(integer + optional_space + pynutil.insert(" "), 0, 1) + vulgar

        self.graph = graph
        self.fst = self.add_tokens(self.graph).optimize()
