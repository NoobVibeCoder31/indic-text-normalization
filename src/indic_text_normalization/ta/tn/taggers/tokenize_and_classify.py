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
    DIGIT,
    SIGMA,
    SPACE,
    TA_BLOCK,
    TA_DIGIT,
    WHITE_SPACE,
    GraphFst,
    delete_extra_space,
    delete_space,
)
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.tn.taggers.date import DateFst
from indic_text_normalization.ta.tn.taggers.decimal import DecimalFst
from indic_text_normalization.ta.tn.taggers.fraction import FractionFst
from indic_text_normalization.ta.tn.taggers.money import MoneyFst
from indic_text_normalization.ta.tn.taggers.ordinal import OrdinalFst
from indic_text_normalization.ta.tn.taggers.punctuation import PunctuationFst
from indic_text_normalization.ta.tn.taggers.telephone import TelephoneFst
from indic_text_normalization.ta.tn.taggers.time import TimeFst
from indic_text_normalization.ta.tn.taggers.whitelist import WhiteListFst
from indic_text_normalization.ta.tn.taggers.word import WordFst


class ClassifyFst(GraphFst):
    """
    Composes all Tamil TN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="tokenize_and_classify", kind="classify", deterministic=deterministic)

        cardinal = CardinalFst(deterministic=deterministic)
        decimal = DecimalFst(cardinal=cardinal, deterministic=deterministic)
        fraction = FractionFst(cardinal=cardinal, deterministic=deterministic)
        time = TimeFst()
        date = DateFst(cardinal=cardinal)
        money = MoneyFst(cardinal=cardinal)
        telephone = TelephoneFst(deterministic=deterministic)
        ordinal = OrdinalFst(cardinal=cardinal, deterministic=deterministic)
        whitelist = WhiteListFst(deterministic=deterministic)
        punctuation = PunctuationFst(deterministic=deterministic)

        classify = (
            pynutil.add_weight(whitelist.fst, 1.01)
            | pynutil.add_weight(telephone.fst, 0.5)
            | pynutil.add_weight(date.fst, 1.04)
            | pynutil.add_weight(time.fst, 1.05)
            | pynutil.add_weight(fraction.fst, 1.06)
            | pynutil.add_weight(decimal.fst, 1.08)
            | pynutil.add_weight(cardinal.fst, 1.1)
            | pynutil.add_weight(money.fst, 1.1)
            | pynutil.add_weight(ordinal.fst, 1.1)
        )

        word_graph = WordFst(punctuation=punctuation, deterministic=deterministic).fst

        punct = (
            pynutil.insert("tokens { ")
            + pynutil.add_weight(punctuation.fst, weight=2.1)
            + pynutil.insert(" }")
        )
        punct = pynini.closure(
            pynini.union(
                pynini.compose(pynini.closure(WHITE_SPACE, 1), delete_extra_space),
                (pynutil.insert(SPACE) + punct),
            ),
            1,
        )

        classify = pynini.union(classify, pynutil.add_weight(word_graph, 100))
        token = pynutil.insert("tokens { ") + classify + pynutil.insert(" }")
        token_plus_punct = (
            pynini.closure(punct + pynutil.insert(SPACE))
            + token
            + pynini.closure(pynutil.insert(SPACE) + punct)
        )

        graph = token_plus_punct + pynini.closure(
            pynini.union(
                pynini.compose(pynini.closure(WHITE_SPACE, 1), delete_extra_space),
                (pynutil.insert(SPACE) + punct + pynutil.insert(SPACE)),
            )
            + token_plus_punct
        )

        graph = delete_space + graph + delete_space
        graph = pynini.union(graph, punct)

        # A hyphen joining a digit to a Tamil word is a separator, e.g. "3.14-அங்கு" -> "3.14 அங்கு".
        # Tamil digits are excluded from the right context so Tamil-digit dates keep their dashes.
        ta_letter = pynini.difference(TA_BLOCK, TA_DIGIT).optimize()
        joiner_hyphen_to_space = pynini.cdrewrite(
            pynini.cross("-", " "), pynini.union(DIGIT, TA_DIGIT), ta_letter, SIGMA
        )

        self.fst = (joiner_hyphen_to_space @ graph).optimize()
