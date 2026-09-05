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

from indic_text_normalization.ta.constants import DIGIT, TA_DIGIT, GraphFst
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

        # A zero denominator has no locative form, so the verbalizer would reject it.
        non_zero = pynini.difference(
            pynini.closure(pynini.union(DIGIT, TA_DIGIT), 1),
            pynini.closure(pynini.union("0", "௦"), 1),
        ).optimize()
        denominator_graph = pynini.compose(non_zero, cardinal_graph).optimize()

        integer = pynutil.insert('integer_part: "') + cardinal_graph + pynutil.insert('"')
        numerator = (
            pynutil.insert('numerator: "')
            + cardinal_graph
            + (pynini.cross("/", '" ') | pynini.cross(" / ", '" '))
        )
        denominator = pynutil.insert('denominator: "') + denominator_graph + pynutil.insert('"')

        graph = pynini.closure(integer + pynini.accep(" "), 0, 1) + (numerator + denominator)

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
