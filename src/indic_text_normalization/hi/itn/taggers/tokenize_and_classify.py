"""
Hindi ITN sentence classifier: the shared taggers bound to the Hindi profile.
"""

import pynini

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
from indic_text_normalization.hi.constants import (
    AND_WORD,
    BY_WORDS,
    ITN_PART_NOUNS,
    LANG,
    LEXICAL_ORDINAL_WORDS,
    PROFILE,
    VULGAR_WORDS,
)
from indic_text_normalization.hi.itn.taggers.cardinal import spoken_pre_map
from indic_text_normalization.hi.itn.taggers.time import ITN_TIME_WORDS
from indic_text_normalization.hi.tn.taggers.cardinal import CardinalFst as TnCardinalFst


class ClassifyFst(ItnClassifyFst):
    """
    Composes all Hindi ITN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        tn_cardinal = TnCardinalFst(deterministic=deterministic)
        cardinal = ItnCardinalFst(
            tn_cardinal,
            pre_map=spoken_pre_map(),
            # एक alone is as often the article ("a") as the numeral.
            ambiguous_words=("एक",),
            deterministic=deterministic,
        )
        # The lexical ordinals are written with their own endings: पहला -> 1ला, छठी -> 6ठी.
        lexical = pynini.union(
            *[
                pynini.cross(word, digit + marker)
                for (digit, marker), word in LEXICAL_ORDINAL_WORDS.items()
            ]
        )
        ordinal = ItnOrdinalFst(
            cardinal,
            tn_cardinal,
            marker=pynini.accep("व"),
            exceptions=lexical,
            deterministic=deterministic,
        )
        super().__init__(
            PROFILE,
            cardinal=cardinal,
            decimal=ItnDecimalFst(
                cardinal, vulgar_words=VULGAR_WORDS, and_word=AND_WORD, deterministic=deterministic
            ),
            fraction=ItnFractionFst(
                cardinal,
                denominator_to_number=None,
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
                bare_scale_words=("लाख", "करोड़", "अरब", "मिलियन", "बिलियन"),
                deterministic=deterministic,
            ),
            telephone=ItnTelephoneFst(
                cardinal, zero_words=("ज़ीरो", "जीरो", "सिफ़र"), deterministic=deterministic
            ),
            prose=ProseFst(LANG, deterministic=deterministic),
            deterministic=deterministic,
        )
