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
Telugu-specific constants: digits, script ranges, sign and point words, case suffixes.
"""

import pynini

from indic_text_normalization.core.scripts import script_digit_fsts

LANG = "te"

_TE_DIGITS = script_digit_fsts("౦")

TE_DIGIT = _TE_DIGITS.digit
TE_NON_ZERO = _TE_DIGITS.non_zero
TE_ZERO = _TE_DIGITS.zero
TE_TO_ASCII_DIGIT = _TE_DIGITS.to_ascii
ASCII_TO_TE_DIGIT = _TE_DIGITS.from_ascii
ASCII_TO_TE_NUMBER = pynini.closure(ASCII_TO_TE_DIGIT).optimize()

# Telugu block U+0C00-U+0C7F, used for context-dependent rewrites.
TE_BLOCK = pynini.union(*[chr(i) for i in range(0x0C00, 0x0C80)]).optimize()
# Letters only (block minus digits), i.e. what may be glued to a number as a suffix.
TE_LETTER = pynini.difference(TE_BLOCK, TE_DIGIT).optimize()
# Consonant letters U+0C15 TELUGU LETTER KA .. U+0C39 TELUGU LETTER HA (inherent -a).
TE_CONSONANT = pynini.union(*[chr(i) for i in range(0x0C15, 0x0C3A)]).optimize()

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
