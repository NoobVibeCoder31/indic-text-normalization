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
Telugu-specific constants: the language profile, script ranges, sign and point words.
"""

import pynini

from indic_text_normalization.core.profile import make_profile

LANG = "te"

# Formal register: a negative sign reads as ఋణ (U+0C0B TELUGU LETTER VOCALIC R);
# the subtraction operator inside an equation reads as మైనస్.
MINUS_WORD = "ఋణ"
MINUS = pynini.union(" ఋణ ").optimize()
OPERATOR_MINUS_WORD = "మైనస్"

# A written leading plus is spoken as ప్లస్ and inverted back to "+" by ITN.
PLUS_WORD = "ప్లస్"

# Spoken between the bounds of a range (10-20 -> పది నుండి ఇరవై).
RANGE_WORD = "నుండి"

# Decimal point word (formal register), plus the spoken variants ITN accepts.
POINT_WORD = "దశాంశం"
POINT_WORDS = [POINT_WORD, "పాయింట్", "పాయింటు", "పాయింట", "పాయిoట్", "డెసిమల్"]

# Case suffixes that may be written glued to a digit (2024లో, 5కి, 100కంటే).
CASE_SUFFIXES = [
    "లో",
    "లోని",
    "లోనూ",
    "లోనే",
    "కి",
    "కు",
    "కీ",
    "కూ",
    "కే",
    "కైనా",
    "తో",
    "తోనే",
    "ని",
    "ను",
    "నే",
    "నుండి",
    "నుంచి",
    "నుండీ",
    "నుంచీ",
    "కంటే",
    "కన్నా",
    "గా",
    "గానే",
    "లా",
    "లాగా",
    "వరకు",
    "వరకూ",
    "దాకా",
    "కోసం",
    "న",
    "లు",
    "ల్లో",
    "ల్లోని",
    "ల్లోనే",
    "లోకి",
    "ల",
    "లలో",
    "లకు",
    "లకి",
    "లను",
    "లతో",
    "లనుండి",
    "లనుంచి",
    "లకంటే",
    "లే",
    "లూ",
    "ే",
    "ూ",
]

# Telugu block U+0C00-U+0C7F; U+0C66 TELUGU DIGIT ZERO opens the digit run.
PROFILE = make_profile(
    LANG,
    zero="౦",
    block=(0x0C00, 0x0C80),
    minus_word=MINUS_WORD,
    operator_minus_word=OPERATOR_MINUS_WORD,
    plus_word=PLUS_WORD,
    range_word=RANGE_WORD,
    range_words=("నుంచి",),
    point_word=POINT_WORD,
    point_words=tuple(POINT_WORDS),
    negative_words=("మైనస్", "రుణ", "ఋణాత్మక", "రుణాత్మక"),
    case_suffixes=tuple(CASE_SUFFIXES),
    counting_one="ఒక",
)

TE_DIGIT = PROFILE.digits.digit
TE_NON_ZERO = PROFILE.digits.non_zero
TE_ZERO = PROFILE.digits.zero
TE_TO_ASCII_DIGIT = PROFILE.digits.to_ascii
ASCII_TO_TE_DIGIT = PROFILE.digits.from_ascii
ASCII_TO_TE_NUMBER = PROFILE.to_native
TE_BLOCK = PROFILE.block
# Letters only (block minus digits), i.e. what may be glued to a number as a suffix.
TE_LETTER = PROFILE.letter
# Consonant letters U+0C15 TELUGU LETTER KA .. U+0C39 TELUGU LETTER HA (inherent -a).
TE_CONSONANT = pynini.union(*[chr(i) for i in range(0x0C15, 0x0C3A)]).optimize()

# Vulgar fraction signs read as their everyday words; a half fuses onto a vowel-final
# integer (ఒకటిన్నర), anything else is "N మరియు <word>".
VULGAR_WORDS = {"½": "అర", "¼": "పావు", "¾": "ముప్పావు"}
HALF_SUFFIX = "న్నర"
AND_WORD = "మరియు"
# Written part nouns after a fraction (3/4 వంతు) that the verbalizer speaks itself.
PART_NOUNS = ("వంతులు", "వంతు")
# Spoken part nouns and the "N by M" word ITN accepts.
ITN_PART_NOUNS = ("వంతులు", "వంతుల", "వంతు", "భాగాలు", "భాగం")
BY_WORDS = ("బై",)
