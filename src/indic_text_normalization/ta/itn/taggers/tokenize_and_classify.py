"""
Tamil ITN sentence classifier composing all ITN taggers.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    DIGIT,
    SPACE,
    TA_DIGIT,
    WHITE_SPACE,
    GraphFst,
    delete_extra_space,
    delete_space,
)
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.itn.taggers.date import DateFst
from indic_text_normalization.ta.itn.taggers.decimal import DecimalFst
from indic_text_normalization.ta.itn.taggers.fraction import FractionFst
from indic_text_normalization.ta.itn.taggers.money import MoneyFst
from indic_text_normalization.ta.itn.taggers.ordinal import OrdinalFst
from indic_text_normalization.ta.itn.taggers.prose import ProseFst
from indic_text_normalization.ta.itn.taggers.punctuation import PunctuationFst
from indic_text_normalization.ta.itn.taggers.telephone import TelephoneFst
from indic_text_normalization.ta.itn.taggers.time import TimeFst
from indic_text_normalization.ta.itn.taggers.word import WordFst
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst as TnCardinalFst


class ClassifyFst(GraphFst):
    """
    Composes all Tamil ITN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="tokenize_and_classify", kind="classify", deterministic=deterministic)

        tn_cardinal = TnCardinalFst(deterministic=deterministic)
        cardinal = CardinalFst(tn_cardinal=tn_cardinal, deterministic=deterministic)
        decimal = DecimalFst(cardinal=cardinal, deterministic=deterministic)
        fraction = FractionFst(cardinal=cardinal, deterministic=deterministic)
        ordinal = OrdinalFst(cardinal=cardinal, deterministic=deterministic)
        date = DateFst(cardinal=cardinal, deterministic=deterministic)
        time = TimeFst(cardinal=cardinal, deterministic=deterministic)
        money = MoneyFst(cardinal=cardinal, deterministic=deterministic)
        telephone = TelephoneFst(deterministic=deterministic)
        punctuation = PunctuationFst(deterministic=deterministic)
        prose = ProseFst(deterministic=deterministic)

        # Already-written numbers (ITN output re-fed) pass through untouched, including
        # a telephone country code (+91) which must not split into punctuation + digits.
        digits_passthrough = (
            pynini.closure(pynini.union("-", "+"), 0, 1)
            + pynini.closure(pynini.union(*"₹$£€¥₩₺৳₦"), 0, 1)
            + pynini.closure(pynini.union(DIGIT, TA_DIGIT), 1)
            + pynini.closure(
                pynini.union(*".:,/") + pynini.closure(pynini.union(DIGIT, TA_DIGIT), 1)
            )
        )
        digits_token = pynutil.insert('name: "') + digits_passthrough + pynutil.insert('"')

        classify = (
            pynutil.add_weight(digits_token, 0.8)
            | pynutil.add_weight(prose.fst, 1.0)
            | pynutil.add_weight(telephone.fst, 0.9)
            | pynutil.add_weight(date.fst, 1.04)
            | pynutil.add_weight(time.fst, 1.05)
            | pynutil.add_weight(fraction.fst, 1.06)
            | pynutil.add_weight(money.fst, 1.07)
            | pynutil.add_weight(decimal.fst, 1.08)
            | pynutil.add_weight(ordinal.fst, 1.09)
            | pynutil.add_weight(cardinal.fst, 1.1)
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

        self.fst = graph.optimize()
