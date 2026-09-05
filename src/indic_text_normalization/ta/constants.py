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
Tamil-specific FST constants plus re-exports of the shared core vocabulary.
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

_TA_DIGITS = script_digit_fsts("௦")

TA_DIGIT = _TA_DIGITS.digit
TA_NON_ZERO = _TA_DIGITS.non_zero
TA_ZERO = _TA_DIGITS.zero
TA_TO_ASCII_DIGIT = _TA_DIGITS.to_ascii
ASCII_TO_TA_DIGIT = _TA_DIGITS.from_ascii

# Tamil block U+0B80-U+0BFF, used for context-dependent rewrites.
TA_BLOCK = pynini.union(*[chr(i) for i in range(0x0B80, 0x0C00)]).optimize()

INPUT_CASED = "cased"
INPUT_LOWER_CASED = "lower_cased"

MINUS_WORD = "மைனஸ்"
MINUS = pynini.union(" மைனஸ் ").optimize()

# Fractional-hour words used by the time grammar.
TA_KAAL = "கால்"
TA_ARAI = "அரை"
TA_MUKKAL = "முக்கால்"
