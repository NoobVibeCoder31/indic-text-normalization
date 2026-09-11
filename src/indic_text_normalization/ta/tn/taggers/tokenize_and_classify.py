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
Tamil TN sentence classifier: the per-class taggers plus the spacing pre-pass.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    ALPHA,
    CHAR,
    CURRENCY_SYMBOLS,
    DIGIT,
    NOT_SPACE,
    SIGMA,
)
from indic_text_normalization.core.punctuation import PunctuationFst
from indic_text_normalization.core.sentence import SentenceClassifyFst
from indic_text_normalization.core.whitelist import WhiteListFst
from indic_text_normalization.core.word import WordFst
from indic_text_normalization.ta.constants import (
    LANG,
    MINUS_WORD,
    RANGE_WORD,
    TA_BLOCK,
    TA_DIGIT,
    TA_LETTER,
)
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.tn.taggers.date import DateFst
from indic_text_normalization.ta.tn.taggers.decimal import DecimalFst
from indic_text_normalization.ta.tn.taggers.fraction import FractionFst
from indic_text_normalization.ta.tn.taggers.measure import MeasureFst
from indic_text_normalization.ta.tn.taggers.money import MoneyFst
from indic_text_normalization.ta.tn.taggers.ordinal import OrdinalFst
from indic_text_normalization.ta.tn.taggers.range import RangeFst
from indic_text_normalization.ta.tn.taggers.telephone import TelephoneFst
from indic_text_normalization.ta.tn.taggers.time import TimeFst

# Case and ordinal suffixes that may be written glued to a digit. Anything
# else glued to a digit is a separate word (5கிலோ -> 5 கிலோ).
CASE_SUFFIXES = [
    "ல்",
    "இல்",
    "க்கு",
    "க்கும்",
    "க்குள்",
    "கள்",
    "களில்",
    "உம்",
    "ும்",
    "ஆக",
    "ஆல்",
    "ால்",
    "ஓடு",
    "உடன்",
    "ஐ",
    "ன்",
    "இன்",
    "லிருந்து",
    "இலிருந்து",
    "த்தில்",
    "த்துக்கு",
    "தான்",
    "ஆம்",
    "ஆவது",
    "வது",
    "ஆவதாக",
    "வதாக",
]

# A case suffix written on % (10%க்கு): சதவீதம் takes its oblique before a suffix.
PERCENT_SUFFIXES = [
    ("%க்கு", " சதவீதத்துக்கு"),
    ("%க்கும்", " சதவீதத்துக்கும்"),
    ("%ஆக", " சதவீதமாக"),
    ("%ஆல்", " சதவீதத்தால்"),
    ("%இல்", " சதவீதத்தில்"),
    ("%ல்", " சதவீதத்தில்"),
    ("%ஆவது", " சதவீதமாவது"),
]

# Symbols the whitelist speaks are always their own token, so the first pass already
# speaks them whether or not they were glued (5#, அ%, ₹* ...).
SPOKEN_SYMBOLS = "#*&^%|~"


def _pre_pass() -> pynini.Fst:
    """
    Spacing rewrites applied to the text before tagging, composed at call time.
    """
    ta_letter = TA_LETTER
    any_digit = pynini.union(DIGIT, TA_DIGIT)
    spaces = pynini.closure(" ")

    # A hyphen joining a digit to a Tamil word (or a Tamil word to a digit) is a
    # separator, e.g. "3.14-அங்கு" -> "3.14 அங்கு", "15-ஜூன்-2024" -> "15 ஜூன் 2024".
    # Tamil digits are excluded from the right context so Tamil-digit dates keep their dashes.
    joiner_hyphen_to_space = pynini.cdrewrite(
        pynini.cross("-", " "), any_digit, ta_letter, SIGMA
    ) @ pynini.cdrewrite(pynini.cross("-", " "), ta_letter, any_digit, SIGMA)

    # Split math/percent symbols off digits so the whitelist can verbalize them,
    # e.g. "5×3=15" -> "5 × 3 = 15", "5%" -> "5 %".
    operator = pynini.union("×", "÷", "%", "=")
    space_after_digit = pynini.cdrewrite(pynutil.insert(" "), any_digit, operator, SIGMA)
    space_before_digit = pynini.cdrewrite(pynutil.insert(" "), operator, any_digit, SIGMA)
    spoken_symbol = pynini.union(*SPOKEN_SYMBOLS)
    split_symbol = pynini.cdrewrite(
        pynutil.insert(" "), NOT_SPACE, spoken_symbol, SIGMA
    ) @ pynini.cdrewrite(pynutil.insert(" "), spoken_symbol, NOT_SPACE, SIGMA)
    # "@" and "_" are spoken too, but stay glued between ASCII letters or digits so an
    # e-mail address or an identifier (user@example.com, a_b) passes through whole.
    edge_symbol = pynini.union("@", "_")
    not_identifier = pynini.difference(NOT_SPACE, pynini.union(ALPHA, edge_symbol))
    split_edge_symbol = pynini.cdrewrite(
        pynutil.insert(" "), not_identifier, edge_symbol, SIGMA
    ) @ pynini.cdrewrite(pynutil.insert(" "), edge_symbol, not_identifier, SIGMA)
    # A hyphen between two amounts is a range: ₹5 - ₹10, ₹5-₹10.
    currency = pynini.union(*CURRENCY_SYMBOLS)
    money_range = pynini.cdrewrite(
        pynini.cross("-", f" {RANGE_WORD} "), any_digit + spaces, spaces + currency, SIGMA
    )
    # "+" is a sign or country code only at a word start before a clean digit run
    # (+91, +5, +919876543210ல்); elsewhere it is the operator word.
    punct_char = pynini.union(*[pynini.escape(c) for c in ".,!?;:()[]{}'\"/"])
    clean_tail = pynini.union(" ", "-", ta_letter, punct_char)
    split_plus_junk = pynini.cdrewrite(
        pynutil.insert(" "),
        pynini.union("[BOS]", " ") + "+",
        pynini.closure(any_digit, 1) + pynini.difference(CHAR, pynini.union(clean_tail, any_digit)),
        SIGMA,
    )
    split_plus = (
        split_plus_junk
        @ pynini.cdrewrite(pynini.cross("+", " + "), NOT_SPACE, any_digit, SIGMA)
        @ pynini.cdrewrite(pynutil.insert(" "), NOT_SPACE, "+", SIGMA)
        @ pynini.cdrewrite(pynutil.insert(" "), "+", pynini.difference(NOT_SPACE, any_digit), SIGMA)
    )
    # "<", ">" and "+" are operators only between two digits; elsewhere they are markup or
    # punctuation. Speaking a lone "+" would break idempotency on the second pass, as a
    # lone "-" once did.
    infix_operators = pynini.cdrewrite(
        pynini.union(
            pynini.cross("<", " விடக் குறைவு "),
            pynini.cross(">", " விட அதிகம் "),
            pynini.cross("+", " கூட்டல் "),
        ),
        any_digit + spaces,
        spaces + any_digit,
        SIGMA,
    )
    trailing_punct = pynini.union(*[pynini.escape(c) for c in "()\"'{}[].,!?%"])

    case_suffixes = pynini.union(*CASE_SUFFIXES)
    ordinal_tail = pynini.union("வத", "ஆவத") + pynini.closure(ta_letter, 1)
    known_suffix = pynini.union(case_suffixes, ordinal_tail).optimize()
    ta_word = pynini.closure(ta_letter, 1)
    unknown_word = pynini.difference(ta_word, known_suffix).optimize()
    boundary = pynini.union(" ", "[EOS]", pynini.difference(CHAR, ta_letter))
    split_digit_word = pynini.cdrewrite(
        pynutil.insert(" "), any_digit, unknown_word + boundary, SIGMA
    )

    # A hyphen between a digit and a case/ordinal suffix belongs to the
    # suffix (3-வது, 2024-ல், 100-க்கு).
    drop_ordinal_hyphen = pynini.cdrewrite(pynutil.delete("-"), any_digit, known_suffix, SIGMA)

    # %க்கு reads as a dative percent word; other case suffixes on % likewise.
    percent_suffix = pynini.cdrewrite(
        pynini.union(*[pynini.cross(a, b) for a, b in PERCENT_SUFFIXES]),
        any_digit,
        pynini.union(" ", "[EOS]", trailing_punct),
        SIGMA,
    )
    # Any other Tamil word glued to % is a separate word.
    percent_word = pynini.cdrewrite(pynutil.insert(" "), "%", ta_letter, SIGMA)

    # A hyphen inside an equation is a minus, not a range: 5-3=2, 10 - 5 = 5.
    subtraction_minus = pynini.cdrewrite(
        pynini.cross("-", f" {MINUS_WORD} "),
        any_digit + spaces,
        spaces + pynini.closure(pynini.union(any_digit, "-", " "), 1) + "=",
        SIGMA,
    )
    # U+2212 MINUS SIGN between digits is subtraction; elsewhere it is a plain minus.
    true_minus = pynini.cdrewrite(
        pynini.cross("−", f" {MINUS_WORD} "), any_digit + spaces, spaces + any_digit, SIGMA
    ) @ pynini.cdrewrite(pynini.cross("−", "-"), "", "", SIGMA)

    return (
        true_minus
        @ drop_ordinal_hyphen
        @ percent_suffix
        @ percent_word
        @ subtraction_minus
        @ infix_operators
        @ space_after_digit
        @ space_before_digit
        @ split_symbol
        @ split_edge_symbol
        @ money_range
        @ split_plus
        @ joiner_hyphen_to_space
        @ split_digit_word
    ).optimize()


class ClassifyFst(SentenceClassifyFst):
    """
    Composes all Tamil TN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        cardinal = CardinalFst(deterministic=deterministic)
        decimal = DecimalFst(cardinal=cardinal, deterministic=deterministic)
        fraction = FractionFst(cardinal=cardinal, deterministic=deterministic)
        measure = MeasureFst(cardinal=cardinal, decimal=decimal, deterministic=deterministic)
        time = TimeFst()
        date = DateFst(cardinal=cardinal)
        money = MoneyFst(cardinal=cardinal)
        telephone = TelephoneFst(cardinal=cardinal, deterministic=deterministic)
        ordinal = OrdinalFst(cardinal=cardinal, deterministic=deterministic)
        number_range = RangeFst(cardinal=cardinal, deterministic=deterministic)
        whitelist = WhiteListFst(LANG, deterministic=deterministic)
        punctuation = PunctuationFst(LANG, speak_equals=True, deterministic=deterministic)

        classify = (
            pynutil.add_weight(whitelist.fst, 1.01)
            | pynutil.add_weight(telephone.fst, 0.5)
            | pynutil.add_weight(measure.fst, 1.03)
            | pynutil.add_weight(date.fst, 1.04)
            | pynutil.add_weight(time.fst, 1.05)
            | pynutil.add_weight(fraction.fst, 1.06)
            | pynutil.add_weight(decimal.fst, 1.08)
            | pynutil.add_weight(number_range.fst, 1.09)
            | pynutil.add_weight(cardinal.fst, 1.1)
            | pynutil.add_weight(money.fst, 1.1)
            | pynutil.add_weight(ordinal.fst, 1.1)
        )
        word = WordFst(punctuation, script=TA_BLOCK, pass_urls=True, deterministic=deterministic)
        super().__init__(
            classify,
            punctuation=punctuation,
            word=word,
            pre_pass=_pre_pass(),
            deterministic=deterministic,
        )
