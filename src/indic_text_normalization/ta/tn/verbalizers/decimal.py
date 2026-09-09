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

from indic_text_normalization.ta.constants import (
    MINUS,
    NOT_QUOTE,
    PLUS_WORD,
    GraphFst,
    insert_space,
)


class DecimalFst(GraphFst):
    """
    Finite state transducer for verbalizing decimal, e.g.
        decimal { negative: "true" integer_part: "பன்னிரண்டு"  fractional_part: "ஐந்து பூஜ்யம் பூஜ்யம் ஆறு" quantity: "பில்லியன்" } -> கழித்தல் பன்னிரண்டு புள்ளி ஐந்து பூஜ்யம் பூஜ்யம் ஆறு
        decimal { integer_part: "பன்னிரண்டு" quantity: "billion" } -> பன்னிரண்டு பில்லியன்

    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="verbalize", deterministic=deterministic)

        delete_space = pynutil.delete(" ")
        self.optional_sign = pynini.closure(
            (
                pynini.cross('negative: "true"', MINUS)
                | pynini.cross('positive: "true"', f" {PLUS_WORD} ")
            )
            + delete_space,
            0,
            1,
        )
        self.integer = (
            pynutil.delete('integer_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        self.fractional_default = (
            pynutil.delete('fractional_part: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )

        self.fractional = pynutil.insert(" புள்ளி ") + self.fractional_default

        self.quantity = (
            delete_space
            + insert_space
            + pynutil.delete('quantity: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )
        self.optional_quantity = pynini.closure(self.quantity, 0, 1)

        # A counting ஒன்று before a scale word reads as ஒரு (ஒரு லட்சம்).
        one_as_oru = pynini.cross("ஒன்று", "ஒரு") | pynini.difference(
            pynini.closure(NOT_QUOTE, 1), pynini.accep("ஒன்று")
        )
        integer_before_quantity = (
            pynutil.delete('integer_part: "') + one_as_oru + pynutil.delete('"')
        )

        graph = self.optional_sign + (
            integer_before_quantity + self.quantity
            | self.integer + delete_space + self.fractional + self.optional_quantity
        )

        self.numbers = graph
        delete_tokens = self.delete_tokens(graph)
        self.fst = delete_tokens.optimize()
