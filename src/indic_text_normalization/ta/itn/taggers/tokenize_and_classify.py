"""
Tamil ITN sentence classifier composing all ITN taggers.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT
from indic_text_normalization.core.punctuation import PunctuationFst
from indic_text_normalization.core.scales import kept_scale_words
from indic_text_normalization.core.sentence import SentenceClassifyFst, written_number_passthrough
from indic_text_normalization.core.word import WordFst
from indic_text_normalization.ta.constants import LANG, TA_BLOCK, TA_DIGIT, TA_LETTER
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.itn.taggers.date import DateFst
from indic_text_normalization.ta.itn.taggers.decimal import DecimalFst
from indic_text_normalization.ta.itn.taggers.fraction import FractionFst
from indic_text_normalization.ta.itn.taggers.money import MoneyFst
from indic_text_normalization.ta.itn.taggers.ordinal import OrdinalFst
from indic_text_normalization.ta.itn.taggers.prose import ProseFst
from indic_text_normalization.ta.itn.taggers.telephone import TelephoneFst
from indic_text_normalization.ta.itn.taggers.time import TimeFst
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst as TnCardinalFst


class ClassifyFst(SentenceClassifyFst):
    """
    Composes all Tamil ITN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        tn_cardinal = TnCardinalFst(deterministic=deterministic)
        cardinal = CardinalFst(tn_cardinal=tn_cardinal, deterministic=deterministic)
        decimal = DecimalFst(cardinal=cardinal, deterministic=deterministic)
        fraction = FractionFst(cardinal=cardinal, deterministic=deterministic)
        ordinal = OrdinalFst(cardinal=cardinal, deterministic=deterministic)
        date = DateFst(cardinal=cardinal, deterministic=deterministic)
        time = TimeFst(cardinal=cardinal, deterministic=deterministic)
        money = MoneyFst(cardinal=cardinal, deterministic=deterministic)
        telephone = TelephoneFst(deterministic=deterministic)
        punctuation = PunctuationFst(LANG, deterministic=deterministic)
        prose = ProseFst(deterministic=deterministic)

        written = written_number_passthrough(
            digit=pynini.union(DIGIT, TA_DIGIT),
            letter=TA_LETTER,
            scale_words=kept_scale_words(LANG),
        )
        classify = (
            pynutil.add_weight(written, 0.8)
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
        word = WordFst(punctuation, script=TA_BLOCK, deterministic=deterministic)
        super().__init__(classify, punctuation=punctuation, word=word, deterministic=deterministic)
