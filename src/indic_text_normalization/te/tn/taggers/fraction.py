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
# limitations under the License.

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, SIGMA, GraphFst
from indic_text_normalization.te.constants import TE_DIGIT
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst

# Vulgar fraction signs and their everyday words: ½ కిలో is అర కిలో, not "one part in two".
VULGAR_WORDS = {"½": "అర", "¼": "పావు", "¾": "ముప్పావు"}
HALF_SUFFIX = "న్నర"
# Nouns a written fraction already contains, so "3/4 వంతు" is not read with the noun twice.
PART_NOUNS = ["వంతులు", "వంతు"]


class FractionFst(GraphFst):
    """
    Finite state transducer for classifying fractions, e.g.
        3/4 -> fraction { numerator: "మూడు" denominator: "నాలుగు" }
        ½ -> fraction { word: "అర" }
        1½ -> fraction { word: "ఒకటిన్నర" }
        2¾ -> fraction { word: "రెండు మరియు ముప్పావు" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="classify", deterministic=deterministic)

        cardinal_graph = cardinal.final_graph

        # A zero or zero-led denominator (1/0, 15/06) has no oblique form.
        any_digit = pynini.union(DIGIT, TE_DIGIT)
        zero = pynini.union("0", "౦")
        non_zero_led = pynini.difference(
            pynini.closure(any_digit, 1), zero + pynini.closure(any_digit)
        ).optimize()
        denominator_graph = pynini.compose(non_zero_led, cardinal_graph).optimize()

        integer = pynutil.insert('integer_part: "') + cardinal_graph + pynutil.insert('"')
        # A zero-led numerator (06/24) is a date fragment, not a fraction.
        numerator_input = pynini.difference(
            pynini.closure(any_digit, 1), zero + pynini.closure(any_digit, 1)
        ).optimize()
        numerator = (
            pynutil.insert('numerator: "')
            + pynini.compose(numerator_input, cardinal_graph)
            + (pynini.cross("/", '" ') | pynini.cross(" / ", '" '))
        )
        denominator = pynutil.insert('denominator: "') + denominator_graph + pynutil.insert('"')
        part_noun = pynini.closure(pynutil.delete(" " + pynini.union(*PART_NOUNS)), 0, 1)

        graph = pynini.closure(integer + pynini.accep(" "), 0, 1) + numerator + denominator
        graph += part_noun
        optional_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" '), 0, 1
        )
        graph = optional_negative + graph

        # Vulgar signs read as words. With an integer, a half fuses onto a vowel-final
        # stem (ఒకటిన్నర, పన్నెండున్నర); anything else is "N మరియు <word>".
        optional_space = pynutil.delete(pynini.closure(" ", 0, 1))
        vulgar_word = pynini.union(*[pynini.cross(s, w) for s, w in VULGAR_WORDS.items()])
        fusable = cardinal_graph @ (SIGMA + pynini.union("ు", "ి"))
        fused_half = fusable + optional_space + pynini.cross("½", HALF_SUFFIX)
        with_integer = cardinal_graph + optional_space + pynutil.insert(" మరియు ") + vulgar_word
        word = pynini.union(
            vulgar_word, pynutil.add_weight(fused_half, -0.1), with_integer
        ) + pynini.closure(pynutil.delete(" " + pynini.union(*PART_NOUNS)), 0, 1)
        graph |= optional_negative + pynutil.insert('word: "') + word + pynutil.insert('"')

        self.graph = graph
        self.fst = self.add_tokens(self.graph).optimize()
