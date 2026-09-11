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

from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.core.graph_utils import GraphFst, SPACE
from indic_text_normalization.te.constants import LANG, MINUS_WORD
from indic_text_normalization.te.morphology import (
    MANY,
    NOT_ONE,
    OBLIQUE_FINAL,
    ONE_AS_OKA,
    optional_suffix_field,
    suffix_sandhi,
)


class MoneyFst(GraphFst):
    """
    Finite state transducer for verbalizing money, e.g.
        money { integer_part: "యాభై" currency_maj: "రూపాయి" } -> యాభై రూపాయలు
        money { integer_part: "ఒకటి" currency_maj: "రూపాయి" } -> ఒక రూపాయి
        money { integer_part: "యాభై" currency_maj: "రూపాయి" fractional_part: "యాభై" currency_min: "centiles" } -> యాభై రూపాయల యాభై పైసలు
        money { currency_maj: "రూపాయి" integer_part: "సున్నా" fractional_part: "యాభై" currency_min: "centiles" } -> యాభై పైసలు
    """

    def __init__(self) -> None:
        super().__init__(name="money", kind="verbalize")

        forms = {
            sg: (pl, obl)
            for sg, pl, obl in (
                r for r in load_labels(data_path(LANG, "money/currency_forms.tsv")) if len(r) >= 3
            )
        }
        major_minor = {
            major: minor
            for major, minor, *_ in load_labels(data_path(LANG, "money/major_minor_currencies.tsv"))
        }

        # A case suffix on the amount attaches to the last currency word (రూపాయలకి).
        optional_suffix = optional_suffix_field()

        integer_one = pynutil.delete('integer_part: "') + ONE_AS_OKA + pynutil.delete('"')
        integer_many = (
            pynutil.delete('integer_part: "') + (MANY @ OBLIQUE_FINAL) + pynutil.delete('"')
        )
        zero_integer = pynutil.delete('integer_part: "సున్నా"')
        minor_field = (
            pynutil.delete('currency_min: "') + pynutil.delete("centiles") + pynutil.delete('"')
        )

        major_only = []
        major_and_minor = []
        minor_only = []
        for major, (major_pl, major_obl) in forms.items():
            if major not in major_minor:
                continue
            minor = major_minor[major]
            minor_pl, _ = forms[minor]
            currency = (
                pynutil.delete('currency_maj: "') + pynutil.delete(major) + pynutil.delete('"')
            )

            major_only.append(
                integer_one + SPACE + currency + pynutil.insert(major) + optional_suffix
            )
            major_only.append(
                integer_many + SPACE + currency + pynutil.insert(major_pl) + optional_suffix
            )

            fraction = (
                pynutil.delete('fractional_part: "')
                + ONE_AS_OKA
                + pynutil.delete('"')
                + SPACE
                + minor_field
                + pynutil.insert(minor)
            ) | (
                pynutil.delete('fractional_part: "')
                + NOT_ONE
                + pynutil.delete('"')
                + SPACE
                + minor_field
                + pynutil.insert(minor_pl)
            )
            fraction = fraction + optional_suffix

            major_and_minor.append(
                integer_one + SPACE + currency + pynutil.insert(major) + SPACE + fraction
            )
            major_and_minor.append(
                integer_many + SPACE + currency + pynutil.insert(major_obl) + SPACE + fraction
            )
            minor_only.append(
                zero_integer + pynutil.delete(SPACE) + currency + pynutil.delete(SPACE) + fraction
            )

        graph = (
            pynini.union(*major_only)
            | pynini.union(*major_and_minor)
            | pynutil.add_weight(pynini.union(*minor_only), -0.1)
        )

        optional_sign = pynini.closure(pynini.cross('negative: "true" ', f"{MINUS_WORD} "), 0, 1)
        graph = (optional_sign + graph) @ suffix_sandhi()
        self.fst = self.delete_tokens(graph).optimize()
