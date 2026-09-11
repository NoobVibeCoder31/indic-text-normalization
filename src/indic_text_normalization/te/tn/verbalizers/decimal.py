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

from indic_text_normalization.core.graph_utils import GraphFst, insert_space, NOT_QUOTE
from indic_text_normalization.te.constants import MINUS, POINT_WORD
from indic_text_normalization.te.morphology import (
    MANY,
    OBLIQUE_FINAL,
    ONE_AS_OKA,
    singularize_quantity,
)


class DecimalFst(GraphFst):
    """
    Finite state transducer for verbalizing decimal, e.g.
        decimal { negative: "true" integer_part: "పన్నెండు" fractional_part: "ఐదు సున్నా" } -> ఋణ పన్నెండు దశాంశం ఐదు సున్నా
        decimal { integer_part: "ఒకటి" quantity: "లక్షలు" } -> ఒక లక్ష
        decimal { integer_part: "ఐదు" quantity: "లక్షలు" } -> ఐదు లక్షలు
    """

    def __init__(self, deterministic: bool = True):
        super().__init__(name="decimal", kind="verbalize", deterministic=deterministic)

        delete_space = pynutil.delete(" ")
        self.optional_sign = pynini.closure(
            pynini.cross('negative: "true"', MINUS) + delete_space, 0, 1
        )
        self.integer = (
            pynutil.delete('integer_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        self.fractional_default = (
            pynutil.delete('fractional_part: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )
        self.fractional = pynutil.insert(f" {POINT_WORD} ") + self.fractional_default

        quantity_value = (
            pynutil.delete('quantity: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        self.quantity = delete_space + insert_space + quantity_value
        self.optional_quantity = pynini.closure(self.quantity, 0, 1)

        # A counting ఒకటి before a scale word reads as ఒక with the singular (ఒక లక్ష);
        # a plural scale word closing the amount takes its oblique before the quantity.
        integer_one = pynutil.delete('integer_part: "') + ONE_AS_OKA + pynutil.delete('"')
        quantity_singular = delete_space + insert_space + singularize_quantity(quantity_value)
        integer_many = (
            pynutil.delete('integer_part: "') + (MANY @ OBLIQUE_FINAL) + pynutil.delete('"')
        )

        graph = self.optional_sign + (
            integer_one + quantity_singular
            | integer_many + self.quantity
            | self.integer + delete_space + self.fractional + self.optional_quantity
        )

        self.numbers = graph
        self.fst = self.delete_tokens(graph).optimize()
