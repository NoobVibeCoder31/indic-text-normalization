"""
Malayalam ITN sentence classifier: the shared taggers bound to the Malayalam profile.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.itn_taggers.cardinal import ItnCardinalFst
from indic_text_normalization.core.itn_taggers.classify import ItnClassifyFst
from indic_text_normalization.core.itn_taggers.date import ItnDateFst
from indic_text_normalization.core.itn_taggers.decimal import ItnDecimalFst
from indic_text_normalization.core.itn_taggers.fraction import ItnFractionFst
from indic_text_normalization.core.itn_taggers.money import ItnMoneyFst
from indic_text_normalization.core.itn_taggers.ordinal import ItnOrdinalFst
from indic_text_normalization.core.itn_taggers.prose import ProseFst
from indic_text_normalization.core.itn_taggers.telephone import ItnTelephoneFst
from indic_text_normalization.core.itn_taggers.time import ItnTimeFst
from indic_text_normalization.ml.constants import BY_WORDS, LANG, PART_NOUNS, PROFILE, VULGAR_WORDS
from indic_text_normalization.ml.itn.taggers.cardinal import spoken_pre_map
from indic_text_normalization.ml.itn.taggers.fraction import DENOMINATOR_TO_NUMBER, mixed_number
from indic_text_normalization.ml.itn.taggers.money import money_inflections
from indic_text_normalization.ml.itn.taggers.time import ITN_TIME_WORDS
from indic_text_normalization.ml.tn.taggers.cardinal import CardinalFst as TnCardinalFst


class ClassifyFst(ItnClassifyFst):
    """
    Composes all Malayalam ITN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        tn_cardinal = TnCardinalFst(deterministic=deterministic)
        cardinal = ItnCardinalFst(
            tn_cardinal,
            pre_map=spoken_pre_map(),
            # ഒന്ന് alone is as often the adverb "just" (ഒന്ന് നോക്കൂ) as the numeral.
            ambiguous_words=("ഒന്ന്",),
            deterministic=deterministic,
        )
        # The written marker is hyphenated: അഞ്ചാം -> 5-ാം, അഞ്ചാമത്തെ -> 5-ാമത്തെ.
        ordinal = ItnOrdinalFst(
            cardinal,
            tn_cardinal,
            marker=pynutil.insert("-") + pynini.accep("ാ"),
            deterministic=deterministic,
        )
        inflected_currency, inflected_minor, scaled_currency = money_inflections()
        super().__init__(
            PROFILE,
            cardinal=cardinal,
            decimal=ItnDecimalFst(
                cardinal, vulgar_words=VULGAR_WORDS, and_word=None, deterministic=deterministic
            ),
            fraction=ItnFractionFst(
                cardinal,
                denominator_to_number=DENOMINATOR_TO_NUMBER,
                part_nouns=PART_NOUNS,
                by_words=BY_WORDS,
                and_word=None,
                mixed=mixed_number(cardinal),
                deterministic=deterministic,
            ),
            ordinal=ordinal,
            date=ItnDateFst(cardinal, deterministic=deterministic),
            time=ItnTimeFst(cardinal, ITN_TIME_WORDS, deterministic=deterministic),
            money=ItnMoneyFst(
                cardinal,
                quantity_nominative={"ലക്ഷത്തി": "ലക്ഷം"},
                bare_scale_words=("ലക്ഷം", "കോടി", "മില്യൻ", "ബില്യൻ"),
                inflected_currency=inflected_currency,
                inflected_minor=inflected_minor,
                scaled_currency=scaled_currency,
                deterministic=deterministic,
            ),
            telephone=ItnTelephoneFst(cardinal, zero_words=("സീറോ",), deterministic=deterministic),
            prose=ProseFst(LANG, deterministic=deterministic),
            deterministic=deterministic,
        )
