"""
The TN tokenizer's spacing pre-pass, shared by every language.
"""

from dataclasses import dataclass

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    ALPHA,
    CHAR,
    CURRENCY_SYMBOLS,
    NOT_SPACE,
    SIGMA,
)
from indic_text_normalization.core.profile import LanguageProfile


@dataclass(frozen=True)
class PrePassWords:
    """
    The language-specific words the pre-pass writes into the text.

    Attributes
    ----------
    spoken_symbols : ``str``
        Symbols the whitelist speaks; each is split into its own token wherever it stands.
    percent_suffixes : ``tuple[tuple[str, str], ...]``
        Written case suffix on ``%`` and its spoken percent word (%కి -> " శాతానికి").
    less_than : ``str | None``
        Spoken ``<`` between two digits, or None to leave it as markup.
    greater_than : ``str | None``
        Spoken ``>`` between two digits.
    division : ``str | None``
        Spoken ``/`` inside an equation (10/2=5), or None to leave it a fraction.
    count_nouns : ``tuple[str, ...]``
        Nouns a bare number is joined to with U+00A0 NO-BREAK SPACE so the cardinal
        tagger reads the pair (1 రోజు -> ఒక రోజు).
    """

    spoken_symbols: str
    percent_suffixes: tuple[tuple[str, str], ...] = ()
    less_than: str | None = None
    greater_than: str | None = None
    division: str | None = None
    count_nouns: tuple[str, ...] = ()


def build_pre_pass(
    profile: LanguageProfile, words: PrePassWords, *, known_suffixes: pynini.Fst
) -> pynini.Fst:
    """
    Spacing rewrites applied to the text before tagging, composed at call time.

    Parameters
    ----------
    profile : ``LanguageProfile``
        The language's profile.
    words : ``PrePassWords``
        The words the rewrites insert.
    known_suffixes : ``pynini.Fst``
        Every case or ordinal suffix that may stay glued to a digit; any other word of the
        script glued to a digit is split off.
    """
    letter = profile.letter
    any_digit = profile.any_digit
    spaces = pynini.closure(" ")
    identity = pynini.cdrewrite(pynini.accep(""), "", "", SIGMA)

    # A hyphen joining a digit to a native word (or a native word to a digit) is a
    # separator, e.g. "3.14-అక్కడ" -> "3.14 అక్కడ", "15-జూన్-2024" -> "15 జూన్ 2024".
    joiner_hyphen_to_space = pynini.cdrewrite(
        pynini.cross("-", " "), any_digit, letter, SIGMA
    ) @ pynini.cdrewrite(pynini.cross("-", " "), letter, any_digit, SIGMA)

    # Split math/percent symbols off digits so the whitelist can verbalize them,
    # e.g. "5×3=15" -> "5 × 3 = 15", "5%" -> "5 %".
    operator = pynini.union("×", "÷", "%", "=")
    space_after_digit = pynini.cdrewrite(pynutil.insert(" "), any_digit, operator, SIGMA)
    space_before_digit = pynini.cdrewrite(pynutil.insert(" "), operator, any_digit, SIGMA)
    spoken_symbol = pynini.union(*words.spoken_symbols)
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
        pynini.cross("-", profile.range_phrase[0]), any_digit + spaces, spaces + currency, SIGMA
    )

    # "+" is a sign or country code only at a word start before a clean digit run
    # (+91, +5, +919876543210కి); elsewhere it is the operator word.
    punct_char = pynini.union(*[pynini.escape(c) for c in ".,!?;:()[]{}'\"/"])
    clean_tail = pynini.union(" ", "-", letter, punct_char)
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
    # A word-initial "+" before a digit is the plus word unless it opens a telephone
    # country code (+91 98765..., +91-44-..., +91 (44) ...), which the telephone tagger
    # reads digit by digit. Speaking it here keeps "+0.0", "+5%" and "+5-6" idempotent.
    # Telephone shapes: a 1-3 digit code, a separator, then at least six more digits
    # possibly split by spaces, hyphens or parentheses; or 11-13 glued digits with an
    # optional suffix (+919876543210కి).
    seps = pynini.closure(pynini.union(" ", "-", "(", ")"))
    country_code_shape = (
        pynini.closure(any_digit, 1, 3)
        + pynini.union(" ", "-")
        + seps
        + pynini.closure(any_digit + seps, 6)
        + pynini.closure(letter)
    )
    country_code_shape |= pynini.closure(any_digit, 11, 13) + pynini.closure(letter)
    # The shape is followed by the rest of the sentence, so the test below is "does the
    # remainder begin with a telephone shape" rather than "is the remainder one".
    country_code_shape = (country_code_shape + pynini.closure(CHAR)).optimize()
    # The right context is anchored with [EOS]: a cdrewrite context matches any prefix,
    # so a set-difference language only works over the whole remainder of the string.
    not_country_code = pynini.difference(any_digit + SIGMA, country_code_shape) + "[EOS]"
    plus_word = pynini.cdrewrite(
        pynini.cross("+", f"{profile.plus_word} "),
        pynini.union("[BOS]", " "),
        not_country_code,
        SIGMA,
    )

    # "<" and ">" are markup except between two digits, where they are comparisons.
    comparison = identity
    if words.less_than and words.greater_than:
        comparison = pynini.cdrewrite(
            pynini.union(
                pynini.cross("<", f" {words.less_than} "),
                pynini.cross(">", f" {words.greater_than} "),
            ),
            any_digit + spaces,
            spaces + any_digit,
            SIGMA,
        )
    trailing_punct = pynini.union(*[pynini.escape(c) for c in "()\"'{}[].,!?%"])

    # Case and ordinal suffixes may stay glued to a digit; anything else glued to a
    # digit is a separate word (5కిలో -> 5 కిలో).
    word = pynini.closure(letter, 1)
    unknown_word = pynini.difference(word, known_suffixes).optimize()
    boundary = pynini.union(" ", "[EOS]", pynini.difference(CHAR, letter))
    split_digit_word = pynini.cdrewrite(
        pynutil.insert(" "), any_digit, unknown_word + boundary, SIGMA
    )

    # A hyphen between a digit and a case/ordinal suffix belongs to the suffix
    # (3-వ, 2024-లో, 100-కి).
    drop_ordinal_hyphen = pynini.cdrewrite(pynutil.delete("-"), any_digit, known_suffixes, SIGMA)

    # %కి reads as a dative percent word; other case suffixes on % likewise.
    percent_suffix = identity
    if words.percent_suffixes:
        percent_suffix = pynini.cdrewrite(
            pynini.union(*[pynini.cross(a, b) for a, b in words.percent_suffixes]),
            any_digit,
            pynini.union(" ", "[EOS]", trailing_punct),
            SIGMA,
        )
    # Any other native word glued to % is a separate word.
    percent_word = pynini.cdrewrite(pynutil.insert(" "), "%", letter, SIGMA)

    # A slash inside an equation is division, not a fraction: 10/2=5.
    division = identity
    if words.division:
        division = pynini.cdrewrite(
            pynini.cross("/", f" {words.division} "),
            any_digit + spaces,
            spaces + pynini.closure(pynini.union(any_digit, "/", " "), 1) + "=",
            SIGMA,
        )
    # A native letter glued to a digit on either side is a separate word (జీ20, 5.మంది).
    letter_digit = pynini.cdrewrite(pynutil.insert(" "), letter, any_digit, SIGMA)
    dot_letter = pynini.cdrewrite(pynutil.insert(" "), any_digit + ".", letter, SIGMA)

    # A hyphen inside an equation is a minus, not a range: 5-3=2, 10 - 5 = 5.
    minus = f" {profile.operator_minus_word} "
    subtraction_minus = pynini.cdrewrite(
        pynini.cross("-", minus),
        any_digit + spaces,
        spaces + pynini.closure(pynini.union(any_digit, "-", " "), 1) + "=",
        SIGMA,
    )
    # U+2212 MINUS SIGN between digits is subtraction; elsewhere it is a plain minus.
    true_minus = pynini.cdrewrite(
        pynini.cross("−", minus), any_digit + spaces, spaces + any_digit, SIGMA
    ) @ pynini.cdrewrite(pynini.cross("−", "-"), "", "", SIGMA)

    # A bare number and a following count noun become one token, joined with U+00A0
    # NO-BREAK SPACE, so the cardinal tagger reads them together and no other class can
    # split the number off the noun.
    join_count_noun = identity
    if words.count_nouns:
        bare_number = pynini.union("[BOS]", " ") + pynini.closure(pynini.union(any_digit, ","), 1)
        join_count_noun = pynini.cdrewrite(
            pynini.cross(" ", " "),
            bare_number,
            pynini.union(*words.count_nouns) + pynini.closure(letter) + boundary,
            SIGMA,
        )

    return (
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
        @ split_edge_symbol
        @ money_range
        @ split_plus
        @ plus_word
        @ joiner_hyphen_to_space
        @ letter_digit
        @ dot_letter
        @ split_digit_word
        @ join_count_noun
    ).optimize()
