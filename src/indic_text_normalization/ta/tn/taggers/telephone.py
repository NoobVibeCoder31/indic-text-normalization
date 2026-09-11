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

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import (
    delete_space,
    DIGIT,
    GraphFst,
    insert_space,
    SIGMA,
)
from indic_text_normalization.ta.constants import LANG, TA_DIGIT
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst

digit_to_word = pynini.string_file(data_path(LANG, "telephone/number.tsv"))

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

    def __init__(self, cardinal: CardinalFst | None = None, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="classify", deterministic=deterministic)

        digit_word = single_digit_to_word + insert_space
        last_digit_word = single_digit_to_word
        delete_sep = pynutil.delete(pynini.union("-", " "))
        optional_sep = pynini.closure(delete_sep, 0, 1)

        # A case suffix on the number lands on the last digit word
        # (9876543210க்கு -> ...பூஜ்யத்துக்கு, 9876543210ல் -> ...பூஜ்யத்தில்).
        dative = pynini.union("க்கு", "க்கும்", "க்குள்")
        last_digit_suffixed = (
            last_digit_word
            @ (SIGMA + pynini.union(pynini.cross("ு", "ில்"), pynini.cross("ம்", "த்தில்")))
        ) + pynutil.delete(pynini.union("ல்", "இல்"))
        last_digit_suffixed |= (
            last_digit_word @ (SIGMA + pynini.union(pynini.accep("ு"), pynini.cross("ம்", "த்து")))
        ) + dative

        def shapes(last: pynini.Fst) -> tuple[pynini.Fst, pynini.Fst]:
            # 10-digit mobile starting 6-9; a 5-5 split with space or dash is common.
            mobile = (
                (mobile_first_digit @ single_digit_to_word)
                + insert_space
                + pynini.closure(digit_word, 3, 3)
                + digit_word
                + optional_sep
                + pynini.closure(digit_word, 4, 4)
                + last
            )

            # Landline: STD code starting 0 (2-4 digits, optionally in parentheses), a
            # dash or space, then a 6-8 digit subscriber number optionally split once.
            std_digits = (
                (zero_digit @ single_digit_to_word)
                + insert_space
                + pynini.closure(digit_word, 1, 3)
            )
            std_code = std_digits | (pynutil.delete("(") + std_digits + pynutil.delete(")"))
            subscriber = (
                pynini.closure(digit_word, 2, 4)
                + pynini.closure(pynutil.delete(" "), 0, 1)
                + pynini.closure(digit_word, 2, 3)
                + last
            )
            landline = std_code + optional_sep + subscriber

            # Toll-free: 1800-XXX-XXXX / 1-800-XXX-XXXX.
            toll_free = (
                pynini.cross("1", "ஒன்று")
                + insert_space
                + optional_sep
                + pynini.closure(digit_word, 3, 3)
                + delete_sep
                + pynini.closure(digit_word, 3, 3)
                + delete_sep
                + pynini.closure(digit_word, 3, 3)
                + last
            )

            # After a country code the STD code drops its leading zero: +91-44-28230000.
            std_no_zero = pynini.closure(digit_word, 2, 4) + delete_sep + subscriber
            return pynini.union(mobile, landline, toll_free), std_no_zero

        plain, cc_landline = shapes(last_digit_word)
        suffixed, cc_landline_suffixed = shapes(last_digit_suffixed)

        country_code = (
            pynutil.insert('country_code: "')
            + pynini.cross("+", "பிளஸ்")
            + insert_space
            + pynini.closure(digit_word, 0, 2)
            + last_digit_word
            + pynutil.insert('" ')
            + pynini.closure(delete_space | pynutil.delete("-"), 0, 1)
        )

        def number_part(inner: pynini.Fst) -> pynini.Fst:
            return pynutil.insert('number_part: "') + inner + pynutil.insert('"')

        graph = pynini.union(
            pynutil.add_weight(country_code + number_part(plain | cc_landline), 0.1),
            pynutil.add_weight(number_part(plain), 0.1),
            pynutil.add_weight(country_code + number_part(suffixed | cc_landline_suffixed), 0.2),
            pynutil.add_weight(number_part(suffixed), 0.2),
        )

        # A standalone +NN (no number following) still reads as பிளஸ் <cardinal>.
        if cardinal is not None:
            standalone_cc = (
                pynutil.insert('country_code: "')
                + pynini.cross("+", "பிளஸ்")
                + insert_space
                + pynini.compose(pynini.closure(any_digit, 1, 3), cardinal.final_graph)
                + pynutil.insert('"')
            )
            graph |= pynutil.add_weight(standalone_cc, 0.3)

        self.final = graph.optimize()
        self.fst = self.add_tokens(self.final)
