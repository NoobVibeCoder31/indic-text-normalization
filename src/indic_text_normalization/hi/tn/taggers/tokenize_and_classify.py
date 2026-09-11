"""
Hindi TN sentence classifier: the shared taggers bound to the Hindi profile.
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
from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.hi.constants import (
    AND_WORD,
    LANG,
    PART_NOUNS,
    PROFILE,
    VULGAR_WORDS,
)
from indic_text_normalization.hi.tn.taggers.cardinal import CardinalFst, lexical_ordinals
from indic_text_normalization.hi.tn.taggers.time import TIME_WORDS

# Symbols the whitelist speaks are always their own token, so the first pass already
# speaks them whether or not they were glued (5#, अ%, ₹* ...).
SPOKEN_SYMBOLS = "#*&^%|~©®™§√∛∞≠≈≤≥±→←↔↑↓"


def _mixed_vulgar(cardinal: CardinalFst) -> pynini.Fst:
    """
    The idiomatic mixed fractions: 1½ -> डेढ़, 2½ -> ढाई, N½ -> साढ़े N, N¼ -> सवा N,
    N¾ -> पौने N+1 (2¾ -> पौने तीन).
    """
    words = {
        int("".join(str(ord(c) - 0x0966) for c in k)): v
        for k, v in load_labels(data_path(LANG, "numbers/teens_and_ties.tsv"), min_fields=2)
    }
    words.update(
        {
            int("".join(str(ord(c) - 0x0966) for c in k)): v
            for k, v in load_labels(data_path(LANG, "numbers/digit.tsv"), min_fields=2)
        }
    )
    optional_space = pynutil.delete(pynini.closure(" ", 0, 1))
    not_one_two = pynini.difference(
        pynini.closure(SIGMA), pynini.union(pynini.accep("एक"), pynini.accep("दो"))
    )
    half = pynini.union(
        pynini.cross("1", "डेढ़"),
        pynini.cross("२", "ढाई"),
        pynini.cross("१", "डेढ़"),
        pynini.cross("2", "ढाई"),
        pynutil.insert("साढ़े ") + (cardinal.final_graph @ not_one_two),
    )
    quarter = pynutil.insert("सवा ") + cardinal.final_graph
    to_native = PROFILE.digits.from_ascii
    three_quarters = pynini.union(
        *[
            pynini.cross(written, f"पौने {words[n + 1]}")
            for n in range(1, 99)
            for written in (
                str(n),
                pynini.shortestpath(str(n) @ pynini.closure(to_native)).string(),
            )
        ]
    )
    return pynini.union(
        half + optional_space + pynutil.delete("½"),
        quarter + optional_space + pynutil.delete("¼"),
        three_quarters + optional_space + pynutil.delete("¾"),
    ).optimize()


class ClassifyFst(TnClassifyFst):
    """
    Composes all Hindi TN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        cardinal = CardinalFst(deterministic=deterministic)
        decimal = DecimalFst(cardinal, deterministic=deterministic)
        pre_pass = build_pre_pass(
            PROFILE,
            PrePassWords(spoken_symbols=SPOKEN_SYMBOLS, division="बटा"),
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
            money=MoneyFst(cardinal, deterministic=deterministic),
            telephone=TelephoneFst(cardinal, deterministic=deterministic),
            ordinal=OrdinalFst(
                cardinal, exceptions=lexical_ordinals(), deterministic=deterministic
            ),
            range=RangeFst(cardinal, deterministic=deterministic),
            pre_pass=pre_pass,
            deterministic=deterministic,
        )
