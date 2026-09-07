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
    CASE_SUFFIXES,
    DIGIT,
    POINT_WORD,
    TE_DIGIT,
    GraphFst,
    insert_space,
)
from indic_text_normalization.te.morphology import OBLIQUE_FINAL
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.te.utils import get_abs_path

currency_graph = pynini.string_file(get_abs_path("data/money/currency.tsv"))

RANGE_WORD = "నుండి"


class MoneyFst(GraphFst):
    """
    Finite state transducer for classifying money, e.g.
        ₹౫౦ -> money { currency_maj: "రూపాయి" integer_part: "యాభై" }
        ₹౫౦.౫౦ -> money { currency_maj: "రూపాయి" integer_part: "యాభై" fractional_part: "యాభై" currency_min: "centiles" }
        ₹౦.౫౦ -> money { currency_maj: "రూపాయి" integer_part: "సున్నా" fractional_part: "యాభై" currency_min: "centiles" }
    The 'centiles' placeholder is resolved by the verbalizer to the minor currency word.

    Args:
        cardinal: CardinalFst
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
        range_amount = cardinal_graph + pynini.cross("-", f" {RANGE_WORD} ") + cardinal_graph
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
        one_digit_padded = pynini.union(DIGIT + pynutil.insert("0"), TE_DIGIT + pynutil.insert("౦"))
        # .05 is five paise: a leading zero in the minor unit is dropped.
        zero_lead = pynini.union(pynutil.delete("0") + DIGIT, pynutil.delete("౦") + TE_DIGIT)
        two_digits = pynini.union(
            pynini.difference(DIGIT, "0") + DIGIT,
            pynini.difference(TE_DIGIT, "౦") + TE_DIGIT,
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

        # ₹5 కోట్లు style: the amount carries an Indian quantity word, and the currency
        # reads after it (ఐదు కోట్ల రూపాయలు). English scale words and the shorthands
        # L/cr/K/M/B are spoken in Telugu (₹2 lakh, ₹15L, $50M).
        te_quantity = pynini.union(
            "కోటి",
            "కోట్లు",
            "కోట్ల",
            "లక్ష",
            "లక్షం",
            "లక్షలు",
            "లక్షల",
            "వెయ్యి",
            "వేలు",
            "వేల",
            "మిలియన్",
            "మిలియన్లు",
            "బిలియన్",
            "బిలియన్లు",
            "ట్రిలియన్",
        )
        english_quantity = pynini.string_map(
            [
                ("thousand", "వేలు"),
                ("lakh", "లక్షలు"),
                ("lakhs", "లక్షలు"),
                ("crore", "కోట్లు"),
                ("crores", "కోట్లు"),
                ("million", "మిలియన్"),
                ("billion", "బిలియన్"),
                ("trillion", "ట్రిలియన్"),
            ]
        )
        shorthand_quantity = pynini.string_map(
            [
                ("L", "లక్షలు"),
                ("cr", "కోట్లు"),
                ("Cr", "కోట్లు"),
                ("CR", "కోట్లు"),
                ("K", "వేలు"),
                ("k", "వేలు"),
                ("M", "మిలియన్"),
                ("B", "బిలియన్"),
            ]
        )
        # ₹1 లక్ష కోట్లు: two scale words may stack.
        quantity_word = (
            pynini.accep(" ") + (te_quantity | english_quantity)
            | pynutil.delete(pynini.closure(" ", 0, 1)) + insert_space + shorthand_quantity
        ) + pynini.closure(pynini.accep(" ") + te_quantity, 0, 1)
        single_frac_digit = pynini.union(DIGIT, TE_DIGIT) @ cardinal_graph
        amount_with_point = cardinal_graph + pynini.closure(
            pynini.cross(".", f" {POINT_WORD} ") + (cardinal.digit_by_digit | single_frac_digit),
            0,
            1,
        )
        # ₹5-10 కోట్లు reads as a range amount.
        amount_with_point |= (
            amount_with_point + pynini.cross("-", f" {RANGE_WORD} ") + amount_with_point
        )
        # The amount takes its oblique before the scale word (₹500 కోట్లు -> ఐదు వందల కోట్ల).
        amount_oblique = (amount_with_point @ OBLIQUE_FINAL).optimize()
        graph_quantity = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + amount_oblique
            + quantity_word
            + pynutil.insert('"')
            + optional_slash_dash
        )

        # ₹50.123: three or more minor digits are not paise; read as a decimal amount.
        long_fraction = pynini.compose(
            pynini.closure(pynini.union(DIGIT, TE_DIGIT), 3), cardinal.digit_by_digit
        )
        graph_long_fraction = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + cardinal_graph
            + pynini.cross(".", f" {POINT_WORD} ")
            + long_fraction
            + pynutil.insert('"')
        )

        # 50/- with no symbol is rupees.
        graph_slash_rupee = (
            pynutil.insert('currency_maj: "రూపాయి"')
            + insert_space
            + integer
            + optional_space
            + pynutil.delete("/-")
        )

        # A trailing .00 minor part is silent (₹1,999.00 -> ...రూపాయలు).
        delete_zero_frac = pynutil.delete(pynini.union(".00", ".౦౦", ".0", ".౦"))
        graph_zero_frac = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer
            + delete_zero_frac
            + optional_slash_dash
        )

        # ₹.50 reads as paise only (symbol currencies only: Rs./రూ. own the dot).
        symbol_currency = pynini.compose(pynini.union("₹", "$", "£", "€", "¥", "₩"), currency_graph)
        currency_symbol_major = (
            pynutil.insert('currency_maj: "') + symbol_currency + pynutil.insert('"')
        )
        graph_bare_paise = (
            currency_symbol_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "సున్నా"')
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

        # ₹150కి: a case suffix on the amount is carried as a field and attached to the
        # currency word by the verbalizer (రూపాయలకి); it may also follow a scale word
        # (₹5 కోట్లకి -> ఐదు కోట్ల రూపాయలకి).
        case_suffix = pynini.union(*CASE_SUFFIXES)
        graph_major_kku = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + (amount_oblique + quantity_word | amount_with_point | cardinal_with_commas)
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

        self.fst = self.add_tokens(graph_currencies.optimize())
