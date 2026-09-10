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

"""
Telugu TN sentence classifier: the shared taggers bound to the Telugu profile.
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
from indic_text_normalization.te.constants import (
    AND_WORD,
    HALF_SUFFIX,
    PART_NOUNS,
    PROFILE,
    VULGAR_WORDS,
)
from indic_text_normalization.te.morphology import OBLIQUE_FINAL, count_nouns
from indic_text_normalization.te.tn.taggers.cardinal import ORDINAL_TAILS, CardinalFst
from indic_text_normalization.te.tn.taggers.time import TIME_WORDS

# A case suffix written on % (10%కి): శాతం takes the oblique శాతాని- before a dative.
PERCENT_SUFFIXES = (
    ("%కి", " శాతానికి"),
    ("%కు", " శాతానికి"),
    ("%కే", " శాతానికే"),
    ("%లో", " శాతంలో"),
    ("%లోనే", " శాతంలోనే"),
    ("%గా", " శాతంగా"),
    ("%తో", " శాతంతో"),
    ("%ని", " శాతాన్ని"),
    ("%కంటే", " శాతం కంటే"),
    ("%కన్నా", " శాతం కన్నా"),
    ("%నుండి", " శాతం నుండి"),
    ("%నుంచి", " శాతం నుంచి"),
    ("%వరకు", " శాతం వరకు"),
    ("%వరకూ", " శాతం వరకూ"),
    ("%దాకా", " శాతం దాకా"),
    ("%కీ", " శాతానికీ"),
    ("%ను", " శాతాన్ని"),
    ("%లా", " శాతంలా"),
    ("%ల", " శాతాల"),
    ("%లలో", " శాతాలలో"),
    ("%లకు", " శాతాలకు"),
    ("%లకి", " శాతాలకి"),
    ("%లను", " శాతాలను"),
    ("%లతో", " శాతాలతో"),
    ("%ే", " శాతమే"),
    ("%ూ", " శాతమూ"),
    ("%లోని", " శాతంలోని"),
    ("%లోనూ", " శాతంలోనూ"),
    ("%కైనా", " శాతానికైనా"),
    ("%గానే", " శాతంగానే"),
    ("%తోనే", " శాతంతోనే"),
    ("%కోసం", " శాతం కోసం"),
)

# Symbols the whitelist speaks are always their own token, so the first pass already
# speaks them whether or not they were glued (5#, అ%, ₹* ...).
SPOKEN_SYMBOLS = "#*&^%|~©®™§√∛∞≠≈≤≥±→←↔↑↓"


def _mixed_half(cardinal: CardinalFst) -> pynini.Fst:
    """
    1½ -> ఒకటిన్నర: the half fuses onto a vowel-final integer (ఒకటిన్నర, పన్నెండున్నర).
    """
    fusable = cardinal.final_graph @ (SIGMA + pynini.union("ు", "ి"))
    optional_space = pynutil.delete(pynini.closure(" ", 0, 1))
    return fusable + optional_space + pynini.cross("½", HALF_SUFFIX)


def _first_ordinal() -> pynini.Fst:
    """
    మొదటి is the idiomatic word for first; an inflected tail still attaches (1వది).
    """
    tails = pynini.union(*[pynini.accep(t) for t in ORDINAL_TAILS])
    return (
        pynini.union(pynini.cross("౧", "మొదటి"), pynini.cross("1", "మొదటి"))
        + pynutil.delete("వ")
        + tails
    )


class ClassifyFst(TnClassifyFst):
    """
    Composes all Telugu TN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        cardinal = CardinalFst(deterministic=deterministic)
        decimal = DecimalFst(cardinal, deterministic=deterministic)
        pre_pass = build_pre_pass(
            PROFILE,
            PrePassWords(
                spoken_symbols=SPOKEN_SYMBOLS,
                percent_suffixes=PERCENT_SUFFIXES,
                less_than="కంటే తక్కువ",
                greater_than="కంటే ఎక్కువ",
                division="భాగించి",
                count_nouns=tuple(count_nouns()),
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
                mixed_vulgar=_mixed_half(cardinal),
                deterministic=deterministic,
            ),
            measure=MeasureFst(cardinal, decimal, deterministic=deterministic),
            time=TimeFst(PROFILE, TIME_WORDS, deterministic=deterministic),
            date=DateFst(cardinal, deterministic=deterministic),
            money=MoneyFst(
                cardinal, amount_before_scale=OBLIQUE_FINAL, deterministic=deterministic
            ),
            telephone=TelephoneFst(cardinal, deterministic=deterministic),
            ordinal=OrdinalFst(cardinal, exceptions=_first_ordinal(), deterministic=deterministic),
            range=RangeFst(cardinal, deterministic=deterministic),
            pre_pass=pre_pass,
            deterministic=deterministic,
        )
