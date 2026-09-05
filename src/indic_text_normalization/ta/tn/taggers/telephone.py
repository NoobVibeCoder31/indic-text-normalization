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
    DIGIT,
    TA_DIGIT,
    GraphFst,
    delete_space,
    insert_space,
)
from indic_text_normalization.ta.utils import get_abs_path

digit_to_word = pynini.string_file(get_abs_path("data/telephone/number.tsv"))

any_digit = pynini.union(DIGIT, TA_DIGIT)
single_digit_to_word = (any_digit @ digit_to_word).optimize()

# Indian mobile numbers start with 6-9.
mobile_first_digit = pynini.union("6", "7", "8", "9", "௬", "௭", "௮", "௯")
zero_digit = pynini.union("0", "௦")


class TelephoneFst(GraphFst):
    """
    Finite state transducer for classifying Indian telephone numbers, e.g.
        9943206870 -> telephone { number_part: "ஒன்பது ஒன்பது நான்கு ..." }
        +91 9876543210 -> telephone { country_code: "பிளஸ் ஒன்பது ஒன்று" number_part: "..." }
        044-28230000 -> telephone { number_part: "பூஜ்யம் நான்கு நான்கு இரண்டு ..." }
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="classify", deterministic=deterministic)

        digit_word = single_digit_to_word + insert_space
        last_digit_word = single_digit_to_word

        # 10-digit mobile starting 6-9, no separators.
        mobile = (
            (mobile_first_digit @ single_digit_to_word)
            + insert_space
            + pynini.closure(digit_word, 8, 8)
            + last_digit_word
        )

        # Landline: STD code starting 0 (2-4 digits), dash, 6-8 digit subscriber number.
        std_code = (
            (zero_digit @ single_digit_to_word) + insert_space + pynini.closure(digit_word, 1, 3)
        )
        subscriber = pynini.closure(digit_word, 5, 7) + last_digit_word
        landline = std_code + pynutil.delete("-") + subscriber

        country_code = (
            pynutil.insert('country_code: "')
            + pynini.cross("+", "பிளஸ்")
            + insert_space
            + pynini.closure(digit_word, 0, 2)
            + last_digit_word
            + pynutil.insert('" ')
            + pynini.closure(delete_space, 0, 1)
        )

        number_part = pynutil.insert('number_part: "') + (mobile | landline) + pynutil.insert('"')

        graph = pynini.union(
            pynutil.add_weight(country_code + number_part, 0.1),
            pynutil.add_weight(number_part, 0.1),
        )

        self.final = graph.optimize()
        self.fst = self.add_tokens(self.final)
