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

from indic_text_normalization.core.graph_utils import (
    delete_space,
    GraphFst,
    insert_space,
    NOT_QUOTE,
    SIGMA,
)
from indic_text_normalization.te.constants import MINUS, TE_CONSONANT
from indic_text_normalization.te.morphology import NOT_ONE, ONE

# The denominator takes the oblique -ింట: the final -ు/-ి is replaced, -ై becomes -య్యింట,
# and a consonant-final word (వంద) simply takes the sign (వందింట).
DENOMINATOR_INTA = SIGMA + pynini.union(
    pynini.cross("ు", "ింట"),
    pynini.cross("ి", "ింట"),
    pynini.cross("ై", "య్యింట"),
    TE_CONSONANT + pynutil.insert("ింట"),
)


class FractionFst(GraphFst):
    """
    Finite state transducer for verbalizing fractions, e.g.
        fraction { numerator: "మూడు" denominator: "నాలుగు" } -> నాలుగింట మూడు వంతులు
        fraction { numerator: "ఒకటి" denominator: "రెండు" } -> రెండింట ఒక వంతు
        fraction { integer_part: "రెండు" numerator: "మూడు" denominator: "నాలుగు" }
            -> రెండు మరియు నాలుగింట మూడు వంతులు
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="verbalize", deterministic=deterministic)

        denominator = (
            pynutil.delete('denominator: "')
            + (pynini.closure(NOT_QUOTE, 1) @ DENOMINATOR_INTA)
            + pynutil.delete('"')
        )
        numerator_word = pynini.union(
            pynini.cross(ONE, "ఒక వంతు"), NOT_ONE + pynutil.insert(" వంతులు")
        )
        numerator = pynutil.delete('numerator: "') + numerator_word + pynutil.delete('"')
        integer = (
            pynutil.delete('integer_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )

        graph = denominator + delete_space + insert_space + numerator
        graph = pynini.closure(integer + delete_space + pynutil.insert(" మరియు "), 0, 1) + graph

        # A vulgar sign travels as its everyday word: అర, ఒకటిన్నర, రెండు మరియు ముప్పావు.
        word = pynutil.delete('word: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')

        optional_sign = pynini.closure(pynini.cross('negative: "true"', MINUS) + delete_space, 0, 1)
        self.graph = optional_sign + (graph | word)
        self.fst = self.delete_tokens(self.graph).optimize()
