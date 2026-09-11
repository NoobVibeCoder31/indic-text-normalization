"""
Kannada ITN sentence classifier: the shared taggers bound to the Kannada profile.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT
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
from indic_text_normalization.kn.constants import (
    AND_WORD,
    BY_WORDS,
    ITN_PART_NOUNS,
    LANG,
    ORDINAL_MARKERS,
    PROFILE,
    VULGAR_WORDS,
)
from indic_text_normalization.kn.itn.taggers.cardinal import spoken_pre_map
from indic_text_normalization.kn.itn.taggers.fraction import DENOMINATOR_TO_NUMBER
from indic_text_normalization.kn.itn.taggers.money import money_inflections
from indic_text_normalization.kn.itn.taggers.time import ITN_TIME_WORDS
from indic_text_normalization.kn.tn.taggers.cardinal import CardinalFst as TnCardinalFst


class ClassifyFst(ItnClassifyFst):
    """
    Composes all Kannada ITN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        tn_cardinal = TnCardinalFst(deterministic=deterministic)
        cardinal = ItnCardinalFst(
            tn_cardinal,
            pre_map=spoken_pre_map(),
            # ಒಂದು alone is as often the article ("a") as the numeral.
            ambiguous_words=("ಒಂದು",),
            deterministic=deterministic,
        )
        markers = pynini.union(*ORDINAL_MARKERS)
        ordinal = ItnOrdinalFst(
            cardinal,
            tn_cardinal,
            marker=pynini.accep("ನ"),
            exceptions=pynini.cross("ಮೊದಲ", "1") + markers,
            deterministic=deterministic,
        )
        inflected_currency, inflected_minor, scaled_currency = money_inflections()
        # A money range takes the ablative on its lower bound: ಐದರಿಂದ ಹತ್ತು ರೂಪಾಯಿ -> ₹5-10.
        range_lower = cardinal.words_to_digits_suffixed @ (
            pynini.closure(DIGIT, 1) + pynutil.delete("ರಿಂದ")
        )
        super().__init__(
            PROFILE,
            cardinal=cardinal,
            decimal=ItnDecimalFst(
                cardinal, vulgar_words=VULGAR_WORDS, and_word=AND_WORD, deterministic=deterministic
            ),
            fraction=ItnFractionFst(
                cardinal,
                denominator_to_number=DENOMINATOR_TO_NUMBER,
                part_nouns=ITN_PART_NOUNS,
                by_words=BY_WORDS,
                and_word=AND_WORD,
                deterministic=deterministic,
            ),
            ordinal=ordinal,
            date=ItnDateFst(cardinal, deterministic=deterministic),
            time=ItnTimeFst(cardinal, ITN_TIME_WORDS, deterministic=deterministic),
            money=ItnMoneyFst(
                cardinal,
                quantity_nominative={},
                bare_scale_words=("ಲಕ್ಷ", "ಕೋಟಿ", "ಮಿಲಿಯನ್", "ಬಿಲಿಯನ್"),
                inflected_currency=inflected_currency,
                inflected_minor=inflected_minor,
                scaled_currency=scaled_currency,
                range_lower=range_lower,
                deterministic=deterministic,
            ),
            telephone=ItnTelephoneFst(
                cardinal, zero_words=("ಶೂನ್ಯ", "ಜೀರೋ"), deterministic=deterministic
            ),
            prose=ProseFst(LANG, deterministic=deterministic),
            deterministic=deterministic,
        )
