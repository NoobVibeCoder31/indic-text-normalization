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
    MINUS,
    NOT_QUOTE,
    GraphFst,
    delete_space,
    insert_space,
)


class FractionFst(GraphFst):
    """
    Finite state transducer for verbalizing fractions, e.g.
        fraction { numerator: "மூன்று" denominator: "நான்கு" } -> நான்கில் மூன்று
        fraction { integer_part: "ஒன்று" numerator: "மூன்று" denominator: "நான்கு" }
            -> ஒன்று மற்றும் நான்கில் மூன்று
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="verbalize", deterministic=deterministic)

        # The locative suffix -இல் replaces the final -உ of the cardinal, with the
        # stem-final consonant doubled for று/டு stems (நான்கு -> நான்கில் is regular).
        denominator_il_suffix = pynini.string_map(
            [
                ("ஒன்று", "ஒன்றில்"),
                ("இரண்டு", "இரண்டில்"),
                ("மூன்று", "மூன்றில்"),
                ("நான்கு", "நான்கில்"),
                ("ஐந்து", "ஐந்தில்"),
                ("ஆறு", "ஆறில்"),
                ("ஏழு", "ஏழில்"),
                ("எட்டு", "எட்டில்"),
                ("ஒன்பது", "ஒன்பதில்"),
                ("பத்து", "பத்தில்"),
                ("பதினொன்று", "பதினொன்றில்"),
                ("பன்னிரண்டு", "பன்னிரண்டில்"),
                ("பதிமூன்று", "பதிமூன்றில்"),
                ("பதினான்கு", "பதினான்கில்"),
                ("பதினைந்து", "பதினைந்தில்"),
                ("பதினாறு", "பதினாறில்"),
                ("பதினேழு", "பதினேழில்"),
                ("பதினெட்டு", "பதினெட்டில்"),
                ("பத்தொன்பது", "பத்தொன்பதில்"),
                ("இருபது", "இருபதில்"),
                ("முப்பது", "முப்பதில்"),
                ("நாற்பது", "நாற்பதில்"),
                ("ஐம்பது", "ஐம்பதில்"),
                ("அறுபது", "அறுபதில்"),
                ("எழுபது", "எழுபதில்"),
                ("எண்பது", "எண்பதில்"),
                ("தொண்ணூறு", "தொண்ணூறில்"),
                ("நூறு", "நூறில்"),
            ]
        ).optimize()

        denominator = (
            pynutil.delete('denominator: "')
            + pynini.closure(NOT_QUOTE) @ denominator_il_suffix
            + pynutil.delete('"')
        )
        numerator = (
            pynutil.delete('numerator: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        integer = (
            pynutil.delete('integer_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )

        graph = denominator + delete_space + insert_space + numerator
        graph = pynini.closure(integer + delete_space + pynutil.insert(" மற்றும் "), 0, 1) + graph

        optional_sign = pynini.closure(pynini.cross('negative: "true"', MINUS) + delete_space, 0, 1)
        self.graph = optional_sign + graph
        self.fst = self.delete_tokens(self.graph).optimize()
