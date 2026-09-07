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

from indic_text_normalization.ta.constants import DIGIT, TA_DIGIT, GraphFst, insert_space
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.utils import get_abs_path

currency_graph = pynini.string_file(get_abs_path("data/money/currency.tsv"))


class MoneyFst(GraphFst):
    """
    Finite state transducer for classifying money, suppletive aware, e.g.
        ₹௫௦ -> money { money { currency_maj: "ரூபாய்" integer_part: "ஐம்பது" }
        ₹௫௦.௫௦ -> money { currency_maj: "ரூபாய்" integer_part: "ஐம்பது" fractional_part: "ஐம்பது" currency_min: "centiles" }
        ₹௦.௫௦ -> money { currency_maj: "ரூபாய்" integer_part: "பூஜ்யம்" fractional_part: "ஐம்பது" currency_min: "centiles" }
    Note that the 'centiles' string is a placeholder to handle by the verbalizer by applying the corresponding minor currency denomination

    Args:
        cardinal: CardinalFst
        decimal: DecimalFst
        deterministic: if True will provide a single transduction option,
            for False multiple transduction are generated (used for audio-based normalization)
    """

    def __init__(self, cardinal: CardinalFst) -> None:
        super().__init__(name="money", kind="classify")

        cardinal_graph = cardinal.final_graph
        cardinal_with_commas = cardinal_graph

        optional_graph_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true"') + insert_space,
            0,
            1,
        )
        currency_major = pynutil.insert('currency_maj: "') + currency_graph + pynutil.insert('"')
        optional_space = pynini.closure(pynini.accep(" "), 0, 1)
        range_amount = cardinal_graph + pynini.cross("-", " முதல் ") + cardinal_graph
        integer = (
            pynutil.insert('integer_part: "')
            + (
                pynutil.add_weight(cardinal_with_commas, -0.1)
                | cardinal_graph
                | pynutil.add_weight(range_amount, -0.05)
            )
            + pynutil.insert('"')
        )
        # ₹50.5 means 50 paise: a lone fractional digit is scaled by ten before lookup.
        one_digit_padded = pynini.union(
            DIGIT + pynutil.insert("0"), TA_DIGIT + pynutil.insert("\u0be6")
        )
        # .05 is five paise: a leading zero in the minor unit is dropped.
        zero_lead = pynini.union(pynutil.delete("0") + DIGIT, pynutil.delete("\u0be6") + TA_DIGIT)
        two_digits = pynini.union(
            pynini.difference(DIGIT, "0") + DIGIT,
            pynini.difference(TA_DIGIT, "\u0be6") + TA_DIGIT,
        )
        fraction_digits = pynini.union(one_digit_padded, zero_lead, two_digits).optimize()
        fraction = (
            pynutil.insert('fractional_part: "')
            + (fraction_digits @ cardinal_graph)
            + pynutil.insert('"')
        )
        currency_minor = (
            pynutil.insert('currency_min: "') + pynutil.insert("centiles") + pynutil.insert('"')
        )

        optional_slash_dash = pynini.closure(
            pynutil.add_weight(
                pynini.closure(pynini.accep(" "), 0, 1) + pynutil.delete("/-"), -0.1
            ),
            0,
            1,
        )

        graph_major_only = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer
            + optional_slash_dash
        )
        graph_major_and_minor = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer
            + optional_space
            + pynini.cross(".", " ")
            + fraction
            + insert_space
            + currency_minor
            + optional_slash_dash
        )

        graph_major_only_suffix = (
            optional_graph_negative
            + integer
            + insert_space
            + optional_space
            + currency_major
            + optional_slash_dash
        )
        graph_major_and_minor_suffix = (
            optional_graph_negative
            + integer
            + optional_space
            + pynini.cross(".", " ")
            + fraction
            + optional_space
            + insert_space
            + currency_minor
            + insert_space
            + currency_major
            + optional_slash_dash
        )

        # ₹5 கோடி style: the amount carries an Indian quantity word, and the
        # currency reads after it (ஐந்து கோடி ரூபாய்). English scale words and the
        # shorthands L/cr/K/M/B are spoken in Tamil (₹2 lakh, ₹15L, $50M).
        tamil_quantity = pynini.union(
            "கோடி", "இலட்சம்", "லட்சம்", "ஆயிரம்", "மில்லியன்", "பில்லியன்", "டிரில்லியன்"
        )
        english_quantity = pynini.string_map(
            [
                ("thousand", "ஆயிரம்"),
                ("lakh", "இலட்சம்"),
                ("lakhs", "இலட்சம்"),
                ("crore", "கோடி"),
                ("crores", "கோடி"),
                ("million", "மில்லியன்"),
                ("billion", "பில்லியன்"),
                ("trillion", "டிரில்லியன்"),
            ]
        )
        shorthand_quantity = pynini.string_map(
            [
                ("L", "இலட்சம்"),
                ("cr", "கோடி"),
                ("Cr", "கோடி"),
                ("CR", "கோடி"),
                ("K", "ஆயிரம்"),
                ("k", "ஆயிரம்"),
                ("M", "மில்லியன்"),
                ("B", "பில்லியன்"),
            ]
        )
        # ₹1 லட்சம் கோடி: two scale words may stack.
        quantity_word = (
            pynini.accep(" ") + (tamil_quantity | english_quantity)
            | pynutil.delete(pynini.closure(" ", 0, 1)) + insert_space + shorthand_quantity
        ) + pynini.closure(pynini.accep(" ") + tamil_quantity, 0, 1)
        single_frac_digit = pynini.union(DIGIT, TA_DIGIT) @ cardinal_graph
        amount_with_point = cardinal_graph + pynini.closure(
            pynini.cross(".", " புள்ளி ") + (cardinal.digit_by_digit | single_frac_digit), 0, 1
        )
        # ₹5-10 கோடி reads as a range amount.
        amount_with_point |= amount_with_point + pynini.cross("-", " முதல் ") + amount_with_point
        graph_quantity = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + amount_with_point
            + quantity_word
            + pynutil.insert('"')
            + optional_slash_dash
        )

        # ₹50.123: three or more minor digits are not paise; read as a decimal amount.
        long_fraction = pynini.compose(
            pynini.closure(pynini.union(DIGIT, TA_DIGIT), 3), cardinal.digit_by_digit
        )
        graph_long_fraction = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + cardinal_graph
            + pynini.cross(".", " புள்ளி ")
            + long_fraction
            + pynutil.insert('"')
        )

        # 50/- with no symbol is rupees.
        graph_slash_rupee = (
            pynutil.insert('currency_maj: "ரூபாய்"')
            + insert_space
            + integer
            + optional_space
            + pynutil.delete("/-")
        )

        # A trailing .00 minor part is silent (₹1,999.00 -> ...ரூபாய்).
        delete_zero_frac = pynutil.delete(pynini.union(".00", ".௦௦"))
        graph_zero_frac = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer
            + delete_zero_frac
            + optional_slash_dash
        )

        # ₹.50 reads as paise only (symbol currencies only: Rs./ரூ. own the dot).
        symbol_currency = pynini.compose(pynini.union("₹", "$", "£", "€", "¥", "₩"), currency_graph)
        currency_symbol_major = (
            pynutil.insert('currency_maj: "') + symbol_currency + pynutil.insert('"')
        )
        graph_bare_paise = (
            currency_symbol_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "பூஜ்யம்"')
            + pynini.cross(".", " ")
            + fraction
            + insert_space
            + currency_minor
        )

        # ₹-500: the sign may follow the symbol.
        negative_after_currency = (
            currency_major
            + optional_space
            + pynutil.insert(" negative: ")
            + pynini.cross("-", '"true"')
            + optional_space
            + insert_space
            + integer
            + optional_slash_dash
        )

        # ₹150க்கு: a case suffix on the amount is carried as a field and attached to
        # the currency word by the verbalizer (ரூபாய்க்கு, ரூபாயாக, ரூபாயில்); it may also
        # follow a scale word (₹5 கோடிக்கு -> ஐந்து கோடி ரூபாய்க்கு).
        case_suffix = pynini.union(
            pynini.accep("க்கு"),
            pynini.accep("க்கும்"),
            pynini.accep("க்குள்"),
            pynini.accep("ஆக"),
            pynini.accep("ஆல்"),
            pynini.accep("இல்"),
            pynini.cross("ல்", "இல்"),
        )
        graph_major_kku = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + (amount_with_point + pynini.closure(quantity_word, 0, 1) | cardinal_with_commas)
            + pynutil.insert('"')
            + pynutil.insert(' suffix: "')
            + case_suffix
            + pynutil.insert('"')
        )

        graph_currencies = (
            pynutil.add_weight(graph_major_kku, -0.1)
            | graph_major_only
            | graph_major_and_minor
            | pynutil.add_weight(graph_quantity, -0.2)
            | pynutil.add_weight(graph_long_fraction, 0.2)
            | pynutil.add_weight(graph_slash_rupee, -0.1)
            | pynutil.add_weight(graph_zero_frac, -0.1)
            | pynutil.add_weight(graph_bare_paise, -0.1)
            | pynutil.add_weight(negative_after_currency, 0.1)
            | pynutil.add_weight(graph_major_only_suffix | graph_major_and_minor_suffix, 0.5)
        )

        graph = graph_currencies.optimize()
        final_graph = self.add_tokens(graph)
        self.fst = final_graph
