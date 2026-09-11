"""
Kannada TN sentence classifier: the shared taggers bound to the Kannada profile.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA
from indic_text_normalization.core.tn_taggers.classify import TnClassifyFst
from indic_text_normalization.core.tn_taggers.date import DateFst
from indic_text_normalization.core.tn_taggers.decimal import DecimalFst
from indic_text_normalization.core.tn_taggers.fraction import FractionFst
from indic_text_normalization.core.tn_taggers.measure import MeasureFst
from indic_text_normalization.core.tn_taggers.money import MoneyFst
from indic_text_normalization.core.tn_taggers.ordinal import OrdinalFst
from indic_text_normalization.core.tn_taggers.prepass import PrePassWords, build_pre_pass
from indic_text_normalization.core.tn_taggers.range import RangeFst
from indic_text_normalization.core.tn_taggers.telephone import TelephoneFst
from indic_text_normalization.core.tn_taggers.time import TimeFst
from indic_text_normalization.kn.constants import (
    AND_WORD,
    CASE_SUFFIXES,
    ORDINAL_MARKERS,
    PART_NOUNS,
    PROFILE,
    VULGAR_FUSED,
    VULGAR_WORDS,
)
from indic_text_normalization.kn.itn.taggers.money import inflect
from indic_text_normalization.kn.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.kn.tn.taggers.time import TIME_WORDS

# A case suffix written on % (5%ರಷ್ಟು): ಪ್ರತಿಶತ is an -ಅ noun (ಪ್ರತಿಶತದಷ್ಟು, ಪ್ರತಿಶತಕ್ಕೆ).
PERCENT_SUFFIXES = (
    ("%ರಷ್ಟು", " ಪ್ರತಿಶತದಷ್ಟು"),
    ("%ರಷ್ಟೇ", " ಪ್ರತಿಶತದಷ್ಟೇ"),
    ("%ಕ್ಕೆ", " ಪ್ರತಿಶತಕ್ಕೆ"),
    ("%ಕ್ಕಿಂತ", " ಪ್ರತಿಶತಕ್ಕಿಂತ"),
    ("%ರಲ್ಲಿ", " ಪ್ರತಿಶತದಲ್ಲಿ"),
    ("%ದಲ್ಲಿ", " ಪ್ರತಿಶತದಲ್ಲಿ"),
    ("%ರ", " ಪ್ರತಿಶತದ"),
    ("%ದ", " ಪ್ರತಿಶತದ"),
    ("%ರಿಂದ", " ಪ್ರತಿಶತದಿಂದ"),
    ("%ದಿಂದ", " ಪ್ರತಿಶತದಿಂದ"),
    ("%ರವರೆಗೆ", " ಪ್ರತಿಶತದವರೆಗೆ"),
)

# Symbols the whitelist speaks are always their own token, so the first pass already
# speaks them whether or not they were glued (5#, ಅ%, ₹* ...).
SPOKEN_SYMBOLS = "#*&^%|~©®™§√∛∞≠≈≤≥±→←↔↑↓"


def _mixed_vulgar(cardinal: CardinalFst) -> pynini.Fst:
    """
    1½ -> ಒಂದೂವರೆ, 2¼ -> ಎರಡೂಕಾಲು, 10¾ -> ಹತ್ತೂಮುಕ್ಕಾಲು: the sign fuses onto a -ು final integer.
    """
    stem = cardinal.final_graph @ (SIGMA + pynutil.delete("ು"))
    optional_space = pynutil.delete(pynini.closure(" ", 0, 1))
    signs = pynini.union(*[pynini.cross(s, w) for s, w in VULGAR_FUSED.items()])
    return stem + optional_space + signs


def _first_ordinal() -> pynini.Fst:
    """
    ಮೊದಲನೇ is the idiomatic word for first (ಒಂದನೇ is accepted by ITN).
    """
    one = pynini.union(pynini.cross("೧", "ಮೊದಲ"), pynini.cross("1", "ಮೊದಲ"))
    return one + pynini.union(*ORDINAL_MARKERS)


def _inflected_quantity() -> pynini.Fst:
    """
    A scale word with a case ending (ಕೋಟಿಗೆ, ಲಕ್ಷದಲ್ಲಿ) to the bare word plus the written
    suffix it stands for, in the form the money tagger's suffix field takes.
    """
    pairs = [
        (inflect(word, written), f'{word}" suffix: "{written}')
        for word in ("ಸಾವಿರ", "ಲಕ್ಷ", "ಕೋಟಿ", "ಮಿಲಿಯನ್", "ಬಿಲಿಯನ್")
        for written in CASE_SUFFIXES
    ]
    return pynini.string_map(pairs).optimize()


class ClassifyFst(TnClassifyFst):
    """
    Composes all Kannada TN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        cardinal = CardinalFst(deterministic=deterministic)
        decimal = DecimalFst(cardinal, deterministic=deterministic)
        pre_pass = build_pre_pass(
            PROFILE,
            PrePassWords(
                spoken_symbols=SPOKEN_SYMBOLS,
                percent_suffixes=PERCENT_SUFFIXES,
                division="ಭಾಗಿಸಿ",
            ),
            known_suffixes=cardinal.known_suffixes,
        )
        super().__init__(
            PROFILE,
            cardinal=cardinal,
            decimal=decimal,
            fraction=FractionFst(
                cardinal,
                vulgar_words=VULGAR_WORDS,
                and_word=AND_WORD,
                part_nouns=PART_NOUNS,
                mixed_vulgar=_mixed_vulgar(cardinal),
                deterministic=deterministic,
            ),
            measure=MeasureFst(cardinal, decimal, deterministic=deterministic),
            time=TimeFst(PROFILE, TIME_WORDS, deterministic=deterministic),
            date=DateFst(cardinal, deterministic=deterministic),
            money=MoneyFst(
                cardinal, inflected_quantity=_inflected_quantity(), deterministic=deterministic
            ),
            telephone=TelephoneFst(cardinal, deterministic=deterministic),
            ordinal=OrdinalFst(cardinal, exceptions=_first_ordinal(), deterministic=deterministic),
            range=RangeFst(cardinal, deterministic=deterministic),
            pre_pass=pre_pass,
            deterministic=deterministic,
        )
