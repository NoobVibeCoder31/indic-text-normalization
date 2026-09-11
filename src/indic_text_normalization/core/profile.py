"""
The per-language facts the shared taggers need: script, digits, sign and point words.
"""

from dataclasses import dataclass

import pynini

from indic_text_normalization.core.graph_utils import DIGIT
from indic_text_normalization.core.scripts import ScriptDigitFsts, script_digit_fsts


@dataclass(frozen=True)
class LanguageProfile:
    """
    Language facts shared by every tagger of one language, TN and ITN alike.

    Attributes
    ----------
    lang : ``str``
        Language code, also the data package name (``te``).
    digits : ``ScriptDigitFsts``
        The native digit FST bundle.
    block : ``pynini.Fst``
        Acceptor for one code point of the script block.
    minus_word : ``str``
        Spoken form of a leading minus sign.
    operator_minus_word : ``str``
        Spoken form of the subtraction operator inside an equation.
    plus_word : ``str``
        Spoken form of a leading plus sign and of the telephone country-code plus.
    range_word : ``str``
        Word spoken between the bounds of a range.
    point_word : ``str``
        Spoken decimal point.
    point_words : ``tuple[str, ...]``
        Every spoken decimal-point variant ITN accepts, ``point_word`` included.
    negative_words : ``tuple[str, ...]``
        Every spoken negative-sign word ITN accepts, ``minus_word`` included.
    positive_words : ``tuple[str, ...]``
        Every spoken positive-sign word ITN accepts, ``plus_word`` included.
    range_words : ``tuple[str, ...]``
        Every spoken range word ITN accepts, ``range_word`` included.
    case_suffixes : ``tuple[str, ...]``
        Case suffixes that may be written glued to a digit (2024లో, 5ന്, 2024ರಲ್ಲಿ).
    counting_one : ``str | None``
        The adjectival "one" that differs from the numeral (ఒక, ഒരു), or None when the
        language uses the numeral itself.
    range_suffix : ``str``
        Word closing a range after the upper bound (Malayalam വരെ in പത്ത് മുതൽ ഇരുപത് വരെ),
        or the empty string.
    """

    lang: str
    digits: ScriptDigitFsts
    block: pynini.Fst
    minus_word: str
    operator_minus_word: str
    plus_word: str
    range_word: str
    point_word: str
    point_words: tuple[str, ...]
    negative_words: tuple[str, ...]
    positive_words: tuple[str, ...]
    range_words: tuple[str, ...]
    case_suffixes: tuple[str, ...]
    counting_one: str | None = None
    range_suffix: str = ""

    @property
    def range_phrase(self) -> tuple[str, str]:
        """
        The text inserted between the bounds of a range and the text appended after them.
        """
        tail = f" {self.range_suffix}" if self.range_suffix else ""
        return f" {self.range_word} ", tail

    @property
    def letter(self) -> pynini.Fst:
        """
        Acceptor for one letter of the script: the block minus its digits.
        """
        return pynini.difference(self.block, self.digits.digit).optimize()

    @property
    def any_digit(self) -> pynini.Fst:
        """
        Acceptor for one digit in either script.
        """
        return pynini.union(DIGIT, self.digits.digit).optimize()

    @property
    def to_native(self) -> pynini.Fst:
        """
        Transducer rewriting a run of ASCII digits into native digits.
        """
        return pynini.closure(self.digits.from_ascii).optimize()

    @property
    def to_ascii(self) -> pynini.Fst:
        """
        Transducer rewriting a run of digits in either script into ASCII digits.
        """
        return pynini.closure(pynini.union(self.digits.to_ascii, DIGIT)).optimize()


def make_profile(
    lang: str,
    *,
    zero: str,
    block: tuple[int, int],
    minus_word: str,
    plus_word: str,
    range_word: str,
    point_word: str,
    case_suffixes: tuple[str, ...],
    operator_minus_word: str | None = None,
    point_words: tuple[str, ...] = (),
    negative_words: tuple[str, ...] = (),
    positive_words: tuple[str, ...] = (),
    range_words: tuple[str, ...] = (),
    counting_one: str | None = None,
    range_suffix: str = "",
) -> LanguageProfile:
    """
    Build a profile from a script's zero digit and block range, filling the ITN variant
    tuples with the TN word when they are not given.

    Parameters
    ----------
    lang : ``str``
        Language code.
    zero : ``str``
        The native zero digit, e.g. U+0C66 TELUGU DIGIT ZERO.
    block : ``tuple[int, int]``
        Inclusive start and exclusive end of the script block, e.g. ``(0x0C00, 0x0C80)``.
    """
    return LanguageProfile(
        lang=lang,
        digits=script_digit_fsts(zero),
        block=pynini.union(*[chr(i) for i in range(*block)]).optimize(),
        minus_word=minus_word,
        operator_minus_word=operator_minus_word or minus_word,
        plus_word=plus_word,
        range_word=range_word,
        point_word=point_word,
        point_words=tuple(dict.fromkeys((point_word, *point_words))),
        negative_words=tuple(dict.fromkeys((minus_word, *negative_words))),
        positive_words=tuple(dict.fromkeys((plus_word, *positive_words))),
        range_words=tuple(dict.fromkeys((range_word, *range_words))),
        case_suffixes=case_suffixes,
        counting_one=counting_one,
        range_suffix=range_suffix,
    )
