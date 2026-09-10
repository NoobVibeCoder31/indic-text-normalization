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

"""
Telugu-specific FST constants plus re-exports of the shared core vocabulary.
"""

import pynini

from indic_text_normalization.core.graph_utils import (
    ALPHA as ALPHA,
)
from indic_text_normalization.core.graph_utils import (
    CHAR as CHAR,
)
from indic_text_normalization.core.graph_utils import (
    DIGIT as DIGIT,
)
from indic_text_normalization.core.graph_utils import (
    MIN_NEG_WEIGHT as MIN_NEG_WEIGHT,
)
from indic_text_normalization.core.graph_utils import (
    NOT_QUOTE as NOT_QUOTE,
)
from indic_text_normalization.core.graph_utils import (
    NOT_SPACE as NOT_SPACE,
)
from indic_text_normalization.core.graph_utils import (
    PUNCT_UNICODE as PUNCT_UNICODE,
)
from indic_text_normalization.core.graph_utils import (
    SIGMA as SIGMA,
)
from indic_text_normalization.core.graph_utils import (
    SPACE as SPACE,
)
from indic_text_normalization.core.graph_utils import (
    UPPER as UPPER,
)
from indic_text_normalization.core.graph_utils import (
    WHITE_SPACE as WHITE_SPACE,
)
from indic_text_normalization.core.graph_utils import (
    TO_LOWER as TO_LOWER,
)
from indic_text_normalization.core.graph_utils import (
    GraphFst as GraphFst,
)
from indic_text_normalization.core.graph_utils import (
    convert_space as convert_space,
)
from indic_text_normalization.core.graph_utils import (
    delete_extra_space as delete_extra_space,
)
from indic_text_normalization.core.graph_utils import (
    delete_preserve_order as delete_preserve_order,
)
from indic_text_normalization.core.graph_utils import (
    delete_space as delete_space,
)
from indic_text_normalization.core.graph_utils import (
    delete_zero_or_one_space as delete_zero_or_one_space,
)
from indic_text_normalization.core.graph_utils import (
    generator_main as generator_main,
)
from indic_text_normalization.core.graph_utils import (
    insert_space as insert_space,
)
from indic_text_normalization.core.scripts import script_digit_fsts

# Telugu digits U+0C66 TELUGU DIGIT ZERO .. U+0C6F TELUGU DIGIT NINE.
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

INPUT_CASED = "cased"
INPUT_LOWER_CASED = "lower_cased"

# Formal register: a negative sign reads as ఋణ (U+0C0B TELUGU LETTER VOCALIC R);
# the subtraction operator inside an equation reads as మైనస్.
MINUS_WORD = "ఋణ"
MINUS = pynini.union(" ఋణ ").optimize()
OPERATOR_MINUS_WORD = "మైనస్"

# A written leading plus is spoken as ప్లస్ and inverted back to "+" by ITN.
PLUS_WORD = "ప్లస్"

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
