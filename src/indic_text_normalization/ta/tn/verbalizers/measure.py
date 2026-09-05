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
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
    insert_space,
)


class MeasureFst(GraphFst):
    """
    Finite state transducer for verbalizing measures, e.g.
        measure { amount: "ஐந்து" units: "கிலோமீட்டர்" } -> ஐந்து கிலோமீட்டர்
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="measure", kind="verbalize", deterministic=deterministic)

        optional_sign = pynini.closure(
            pynini.cross('negative: "true"', "மைனஸ் ") + delete_space, 0, 1
        )
        # A whole-field ஒன்று before the unit noun reads as ஒரு.
        one_as_oru = pynini.cross("ஒன்று", "ஒரு") | pynini.difference(
            pynini.closure(NOT_QUOTE, 1), pynini.accep("ஒன்று")
        )
        amount = pynutil.delete('amount: "') + one_as_oru + pynutil.delete('"')
        units = pynutil.delete('units: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')

        graph = optional_sign + amount + delete_space + insert_space + units + delete_preserve_order
        self.fst = self.delete_tokens(graph).optimize()
