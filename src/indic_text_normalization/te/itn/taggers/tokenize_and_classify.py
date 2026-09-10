"""
Telugu ITN sentence classifier: the shared taggers bound to the Telugu profile.
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
from indic_text_normalization.te.constants import (
    AND_WORD,
    BY_WORDS,
    ITN_PART_NOUNS,
    LANG,
    PROFILE,
    VULGAR_WORDS,
)
from indic_text_normalization.te.itn.taggers.cardinal import extra_inverted, spoken_pre_map
from indic_text_normalization.te.itn.taggers.time import ITN_TIME_WORDS
from indic_text_normalization.te.tn.taggers.cardinal import ORDINAL_TAILS
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst as TnCardinalFst
from indic_text_normalization.te.tn.verbalizers.fraction import DENOMINATOR_INTA


class ClassifyFst(ItnClassifyFst):
    """
    Composes all Telugu ITN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        tn_cardinal = TnCardinalFst(deterministic=deterministic)
        cardinal = ItnCardinalFst(
            tn_cardinal,
            pre_map=spoken_pre_map(),
            extra_inverted=extra_inverted(tn_cardinal),
            # A bare plural marker ల is not a suffix: వేల / లక్షల alone are generic plurals.
            suffix_exclusions=("ల", "లు"),
            deterministic=deterministic,
        )
        # The colloquial -ో ordinal is written with the plain -వ marker; మొదటి is first.
        tails = pynini.union(*[pynini.accep(t) for t in ORDINAL_TAILS])
        ordinal = ItnOrdinalFst(
            cardinal,
            tn_cardinal,
            marker=pynini.cross("వో", "వ") | pynini.accep("వ"),
            exceptions=pynini.cross("మొదటి", "1వ") + tails,
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
                denominator_to_number=pynini.invert(DENOMINATOR_INTA),
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
                quantity_nominative={"కోట్ల": "కోట్లు", "లక్షల": "లక్షలు"},
                bare_scale_words=("లక్ష", "కోటి", "మిలియన్", "బిలియన్"),
                deterministic=deterministic,
            ),
            telephone=ItnTelephoneFst(
                cardinal, zero_words=("సున్న", "జీరో"), deterministic=deterministic
            ),
            prose=ProseFst(LANG, deterministic=deterministic),
            deterministic=deterministic,
        )
