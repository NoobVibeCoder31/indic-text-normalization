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

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import (
    CASE_SUFFIXES,
    CHAR,
    DIGIT,
    NOT_SPACE,
    OPERATOR_MINUS_WORD,
    SIGMA,
    SPACE,
    TE_DIGIT,
    TE_LETTER,
    WHITE_SPACE,
    GraphFst,
    delete_extra_space,
    delete_space,
)
from indic_text_normalization.te.tn.taggers.cardinal import ORDINAL_TAILS, CardinalFst
from indic_text_normalization.te.tn.taggers.date import DateFst
from indic_text_normalization.te.tn.taggers.decimal import DecimalFst
from indic_text_normalization.te.tn.taggers.fraction import FractionFst
from indic_text_normalization.te.tn.taggers.measure import MeasureFst
from indic_text_normalization.te.tn.taggers.money import MoneyFst
from indic_text_normalization.te.tn.taggers.ordinal import OrdinalFst
from indic_text_normalization.te.tn.taggers.punctuation import PunctuationFst
from indic_text_normalization.te.tn.taggers.range import RangeFst
from indic_text_normalization.te.tn.taggers.telephone import TelephoneFst
from indic_text_normalization.te.tn.taggers.time import TimeFst
from indic_text_normalization.te.tn.taggers.whitelist import WhiteListFst
from indic_text_normalization.te.tn.taggers.word import WordFst

# A case suffix written on % (10%కి): శాతం takes the oblique శాతాని- before a dative.
PERCENT_SUFFIXES = [
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
]


class ClassifyFst(GraphFst):
    """
    Composes all Telugu TN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="tokenize_and_classify", kind="classify", deterministic=deterministic)

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
        whitelist = WhiteListFst(deterministic=deterministic)
        punctuation = PunctuationFst(deterministic=deterministic)

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

        word_graph = WordFst(punctuation=punctuation, deterministic=deterministic).fst

        punct = (
            pynutil.insert("tokens { ")
            + pynutil.add_weight(punctuation.fst, weight=2.1)
            + pynutil.insert(" }")
        )
        punct = pynini.closure(
            pynini.union(
                pynini.compose(pynini.closure(WHITE_SPACE, 1), delete_extra_space),
                (pynutil.insert(SPACE) + punct),
            ),
            1,
        )

        classify = pynini.union(classify, pynutil.add_weight(word_graph, 100))
        token = pynutil.insert("tokens { ") + classify + pynutil.insert(" }")
        token_plus_punct = (
            pynini.closure(punct + pynutil.insert(SPACE))
            + token
            + pynini.closure(pynutil.insert(SPACE) + punct)
        )

        graph = token_plus_punct + pynini.closure(
            pynini.union(
                pynini.compose(pynini.closure(WHITE_SPACE, 1), delete_extra_space),
                (pynutil.insert(SPACE) + punct + pynutil.insert(SPACE)),
            )
            + token_plus_punct
        )

        graph = delete_space + graph + delete_space
        graph = pynini.union(graph, punct)

        # A hyphen joining a digit to a Telugu word (or a Telugu word to a digit) is a
        # separator, e.g. "3.14-అక్కడ" -> "3.14 అక్కడ", "15-జూన్-2024" -> "15 జూన్ 2024".
        # Telugu digits are excluded from the right context so Telugu-digit dates keep their dashes.
        te_letter = TE_LETTER
        any_digit = pynini.union(DIGIT, TE_DIGIT)
        joiner_hyphen_to_space = pynini.cdrewrite(
            pynini.cross("-", " "), any_digit, te_letter, SIGMA
        ) @ pynini.cdrewrite(pynini.cross("-", " "), te_letter, any_digit, SIGMA)

        # Split math/percent symbols off digits so the whitelist can verbalize them,
        # e.g. "5×3=15" -> "5 × 3 = 15", "5%" -> "5 %".
        operator = pynini.union("×", "÷", "%", "=")
        space_after_digit = pynini.cdrewrite(pynutil.insert(" "), any_digit, operator, SIGMA)
        space_before_digit = pynini.cdrewrite(pynutil.insert(" "), operator, any_digit, SIGMA)
        # Symbols the whitelist speaks are always their own token, so the first pass
        # already speaks them whether or not they were glued (5#, అ%, ₹* ...).
        spoken_symbol = pynini.union(
            "#",
            "*",
            "&",
            "^",
            "%",
            "|",
            "~",
            "©",
            "®",
            "™",
            "§",
            "√",
            "∛",
            "∞",
            "≠",
            "≈",
            "≤",
            "≥",
            "±",
            "→",
            "←",
            "↔",
            "↑",
            "↓",
        )
        split_symbol = pynini.cdrewrite(
            pynutil.insert(" "), NOT_SPACE, spoken_symbol, SIGMA
        ) @ pynini.cdrewrite(pynutil.insert(" "), spoken_symbol, NOT_SPACE, SIGMA)
        # "+" is a sign or country code only at a word start before a clean digit run
        # (+91, +5, +919876543210కి); elsewhere it is the operator word.
        punct_char = pynini.union(*[pynini.escape(c) for c in ".,!?;:()[]{}'\"/"])
        clean_tail = pynini.union(" ", "-", te_letter, punct_char)
        split_plus_junk = pynini.cdrewrite(
            pynutil.insert(" "),
            pynini.union("[BOS]", " ") + "+",
            pynini.closure(any_digit, 1)
            + pynini.difference(CHAR, pynini.union(clean_tail, any_digit)),
            SIGMA,
        )
        split_plus = (
            split_plus_junk
            @ pynini.cdrewrite(pynini.cross("+", " + "), NOT_SPACE, any_digit, SIGMA)
            @ pynini.cdrewrite(pynutil.insert(" "), NOT_SPACE, "+", SIGMA)
            @ pynini.cdrewrite(
                pynutil.insert(" "), "+", pynini.difference(NOT_SPACE, any_digit), SIGMA
            )
        )
        # A word-initial "+" before a digit is the word ప్లస్ unless it opens a telephone
        # country code (+91 98765..., +91-44-..., +91 (44) ...), which the telephone tagger
        # reads digit by digit. Speaking it here keeps "+0.0", "+5%" and "+5-6" idempotent.
        # Telephone shapes: a 1-3 digit code, a separator, then at least six more digits
        # possibly split by spaces, hyphens or parentheses (+91 98765 43210, +91-44-28230000,
        # +91 (44) 2823 0000); or 11-13 glued digits with an optional suffix (+919876543210కి).
        seps = pynini.closure(pynini.union(" ", "-", "(", ")"))
        country_code_shape = (
            pynini.closure(any_digit, 1, 3)
            + pynini.union(" ", "-")
            + seps
            + pynini.closure(any_digit + seps, 6)
            + pynini.closure(te_letter)
        )
        country_code_shape |= pynini.closure(any_digit, 11, 13) + pynini.closure(te_letter)
        country_code_shape = country_code_shape.optimize()
        # The right context is anchored with [EOS]: a cdrewrite context matches any prefix,
        # so a set-difference language only works over the whole remainder of the string.
        not_country_code = pynini.difference(any_digit + SIGMA, country_code_shape) + "[EOS]"
        plus_word = pynini.cdrewrite(
            pynini.cross("+", "ప్లస్ "), pynini.union("[BOS]", " "), not_country_code, SIGMA
        )

        # "<" and ">" are markup except between two digits, where they are comparisons.
        spaces = pynini.closure(" ")
        comparison = pynini.cdrewrite(
            pynini.union(pynini.cross("<", " కంటే తక్కువ "), pynini.cross(">", " కంటే ఎక్కువ ")),
            any_digit + spaces,
            spaces + any_digit,
            SIGMA,
        )
        trailing_punct = pynini.union(*[pynini.escape(c) for c in "()\"'{}[].,!?%"])

        # Case and ordinal suffixes that may be written glued to a digit. Anything
        # else glued to a digit is a separate word (5కిలో -> 5 కిలో).
        case_suffixes = pynini.union(*CASE_SUFFIXES)
        ordinal_tail = pynini.union(
            pynini.accep("వ") + pynini.union(*[pynini.accep(t) for t in ORDINAL_TAILS]),
            pynini.accep("వో"),
        )
        known_suffix = pynini.union(case_suffixes, ordinal_tail).optimize()
        te_word = pynini.closure(te_letter, 1)
        unknown_word = pynini.difference(te_word, known_suffix).optimize()
        boundary = pynini.union(" ", "[EOS]", pynini.difference(CHAR, te_letter))
        split_digit_word = pynini.cdrewrite(
            pynutil.insert(" "), any_digit, unknown_word + boundary, SIGMA
        )

        # A hyphen between a digit and a case/ordinal suffix belongs to the
        # suffix (3-వ, 2024-లో, 100-కి).
        drop_ordinal_hyphen = pynini.cdrewrite(pynutil.delete("-"), any_digit, known_suffix, SIGMA)

        # %కి reads as a dative percent word; other case suffixes on % likewise.
        percent_suffix = pynini.cdrewrite(
            pynini.union(*[pynini.cross(a, b) for a, b in PERCENT_SUFFIXES]),
            any_digit,
            pynini.union(" ", "[EOS]", trailing_punct),
            SIGMA,
        )
        # Any other Telugu word glued to % is a separate word.
        percent_word = pynini.cdrewrite(pynutil.insert(" "), "%", te_letter, SIGMA)

        # A slash inside an equation is division, not a fraction: 10/2=5.
        division = pynini.cdrewrite(
            pynini.cross("/", " భాగించి "),
            any_digit + spaces,
            spaces + pynini.closure(pynini.union(any_digit, "/", " "), 1) + "=",
            SIGMA,
        )
        # A Telugu letter glued to a digit on either side is a separate word (జీ20, 5.మంది).
        letter_digit = pynini.cdrewrite(pynutil.insert(" "), te_letter, any_digit, SIGMA)
        dot_letter = pynini.cdrewrite(pynutil.insert(" "), any_digit + ".", te_letter, SIGMA)

        # A hyphen inside an equation is a minus, not a range: 5-3=2, 10 - 5 = 5.
        subtraction_minus = pynini.cdrewrite(
            pynini.cross("-", f" {OPERATOR_MINUS_WORD} "),
            any_digit + spaces,
            spaces + pynini.closure(pynini.union(any_digit, "-", " "), 1) + "=",
            SIGMA,
        )
        # U+2212 MINUS SIGN between digits is subtraction; elsewhere it is a plain minus.
        true_minus = pynini.cdrewrite(
            pynini.cross("−", f" {OPERATOR_MINUS_WORD} "),
            any_digit + spaces,
            spaces + any_digit,
            SIGMA,
        ) @ pynini.cdrewrite(pynini.cross("−", "-"), "", "", SIGMA)

        pre_pass = (
            true_minus
            @ drop_ordinal_hyphen
            @ percent_suffix
            @ percent_word
            @ subtraction_minus
            @ division
            @ comparison
            @ space_after_digit
            @ space_before_digit
            @ split_symbol
            @ split_plus
            @ plus_word
            @ joiner_hyphen_to_space
            @ letter_digit
            @ dot_letter
            @ split_digit_word
        ).optimize()
        self.fst = (pre_pass @ graph).optimize()
