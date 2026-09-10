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
Tamil-specific constants: digits, script ranges, sign words and clock bounds.
"""

import pynini

from indic_text_normalization.core.scripts import script_digit_fsts

LANG = "ta"

_TA_DIGITS = script_digit_fsts("௦")

TA_DIGIT = _TA_DIGITS.digit
TA_NON_ZERO = _TA_DIGITS.non_zero
TA_ZERO = _TA_DIGITS.zero
TA_TO_ASCII_DIGIT = _TA_DIGITS.to_ascii
ASCII_TO_TA_DIGIT = _TA_DIGITS.from_ascii

# Tamil block U+0B80-U+0BFF, used for context-dependent rewrites.
TA_BLOCK = pynini.union(*[chr(i) for i in range(0x0B80, 0x0C00)]).optimize()
# The letters and vowel signs of the block, i.e. everything but the Tamil digits.
TA_LETTER = pynini.difference(TA_BLOCK, TA_DIGIT).optimize()

MINUS_WORD = "மைனஸ்"
MINUS = pynini.union(" மைனஸ் ").optimize()
PLUS_WORD = "பிளஸ்"

# Spoken between the bounds of a range (10-20 -> பத்து முதல் இருபது).
RANGE_WORD = "முதல்"

# Clock bounds for the ITN direction. TN's data/time/hours.tsv still lists hour 24
# because it accepts the written 24:00; ITN stops at 23 because இருபத்துநான்கு மணி reads
# as a duration, not a clock time.
CLOCK_MAX_HOUR = 23
CLOCK_MAX_MINUTE = 59

# Fractional-hour words used by the time grammar.
TA_KAAL = "கால்"
TA_ARAI = "அரை"
TA_MUKKAL = "முக்கால்"
