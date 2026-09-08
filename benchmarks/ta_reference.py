"""
Pure-Python reference verbalizer for Tamil text normalization (written -> spoken).

It reuses only the lexical TSV tables shipped with the library and re-implements the
composition rules independently of the WFST grammar, so that it can produce the
``expected`` column of the benchmark dataset.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from indic_text_normalization.core.utils import data_path, load_labels

TAMIL_DIGITS = "௦௧௨௩௪௫௬௭௮௯"
_TO_ASCII = str.maketrans(TAMIL_DIGITS, "0123456789")
_TO_TAMIL = str.maketrans("0123456789", TAMIL_DIGITS)

ZERO = "பூஜ்யம்"
HUNDRED = "நூறு"
HUNDRED_STEM = "நூற்று"
NINE_HUNDRED = "தொள்ளாயிரம்"
NINE_HUNDRED_STEM = "தொள்ளாயிரத்து"
THOUSAND = "ஆயிரம்"
LAKH = "இலட்சம்"
CRORE = "கோடி"
MINUS = "மைனஸ்"
POINT = "புள்ளி"
PLUS = "பிளஸ்"
AND = "மற்றும்"
RANGE_JOINER = "முதல்"
HOUR = "மணி"
MINUTE = "நிமிடம்"
SECOND = "வினாடி"
ORU = "ஒரு"
ONE = "ஒன்று"
FIRST_STEM = "முதலா"

# Fused stems the grammar uses for 151-189 (exact tens 150-180 stay spaced).
SPECIAL_TENS_STEM = {5: "நூற்றைம்பத்து", 6: "நூற்றறுபத்து", 7: "நூற்றெழுபத்து", 8: "நூற்றெண்பத்து"}
ORU_SCALES = (LAKH, CRORE)

INDIAN_COMMA_RE = re.compile(r"^\d{1,2}(?:,\d{2})+(?:,\d{3})?$")
INTL_COMMA_RE = re.compile(r"^\d{1,3}(?:,\d{3})+$")

VULGAR_FRACTIONS = {"½": (1, 2), "¼": (1, 4), "¾": (3, 4)}


def to_ascii_digits(text: str) -> str:
    """
    Map Tamil digits U+0BE6..U+0BEF to ASCII digits.
    """
    return text.translate(_TO_ASCII)


def to_tamil_digits(text: str) -> str:
    """
    Map ASCII digits to Tamil digits U+0BE6..U+0BEF.
    """
    return text.translate(_TO_TAMIL)


def nfc(text: str) -> str:
    """
    NFC-normalize ``text``.
    """
    return unicodedata.normalize("NFC", text)


def _table(*parts: str) -> dict[str, str]:
    """
    Load a two-column TSV under ``ta/data`` as a dict with ASCII-digit keys.
    """
    rows = load_labels(data_path("ta", *parts))
    return {to_ascii_digits(r[0]): r[1] for r in rows if len(r) >= 2}


def _int_table(*parts: str) -> dict[int, str]:
    return {int(k): v for k, v in _table(*parts).items()}


@dataclass(frozen=True)
class Tables:
    """
    Lexical tables shared by every reference rule.
    """

    digit: dict[int, str]
    tens: dict[int, str]
    hundreds_stem: dict[int, str]
    hundreds_exact: dict[int, str]
    days: dict[int, str]
    months: dict[int, str]
    hours: dict[int, str]
    minutes: dict[int, str]
    seconds: dict[int, str]
    currency: dict[str, str]
    minor: dict[str, str]
    units: dict[str, str]
    abbreviations: dict[str, str]
    symbols: dict[str, str]


@lru_cache(maxsize=1)
def tables() -> Tables:
    """
    Load and cache all lexical tables.
    """
    return Tables(
        digit=_int_table("numbers", "digit.tsv"),
        tens=_int_table("numbers", "teens_and_ties.tsv"),
        hundreds_stem=_int_table("numbers", "hundreds_combined.tsv"),
        hundreds_exact=_int_table("numbers", "hundreds_exact.tsv"),
        days=_int_table("date", "days.tsv"),
        months=_int_table("date", "months.tsv"),
        hours=_int_table("time", "hours.tsv"),
        minutes=_int_table("time", "minutes.tsv"),
        seconds=_int_table("time", "seconds.tsv"),
        currency=_table("money", "currency.tsv"),
        minor=_table("money", "major_minor_currencies.tsv"),
        units=_table("measure", "unit.tsv"),
        abbreviations=_table("whitelist", "abbreviations.tsv"),
        symbols=_table("whitelist", "symbol.tsv"),
    )


# --------------------------------------------------------------------------- cardinal


def _below_hundred(n: int) -> str:
    t = tables()
    if n == 0:
        return ZERO
    if n < 10:
        return t.digit[n]
    return t.tens[n]


def _hundreds(n: int) -> str:
    t = tables()
    h, r = divmod(n, 100)
    if h == 1:
        if r == 0:
            return HUNDRED
        if r < 10:
            return f"{HUNDRED_STEM} {t.digit[r]}"
        ten, d = divmod(r, 10)
        if ten in SPECIAL_TENS_STEM and d != 0:
            return f"{SPECIAL_TENS_STEM[ten]} {t.digit[d]}"
        return f"{HUNDRED_STEM} {t.tens[r]}"
    if h == 9:
        if r == 0:
            return NINE_HUNDRED
        return f"{NINE_HUNDRED_STEM} {_below_hundred(r)}"
    if r == 0:
        return t.hundreds_exact[h * 100]
    return f"{t.hundreds_stem[h]} {_below_hundred(r)}"


def _up_to_999(n: int) -> str:
    return _hundreds(n) if n >= 100 else _below_hundred(n)


def _indian_groups(n: int) -> str:
    """
    Verbalize 1..99,99,99,999 with Indian scale words, before style rewrites.
    """
    crore, rest = divmod(n, 10**7)
    lakh, rest = divmod(rest, 10**5)
    thousand, rest = divmod(rest, 1000)
    parts = []
    if crore:
        parts.append(f"{_below_hundred(crore)} {CRORE}")
    if lakh:
        parts.append(f"{_below_hundred(lakh)} {LAKH}")
    if thousand:
        parts.append(f"{_below_hundred(thousand)} {THOUSAND}")
    if rest or not parts:
        parts.append(_up_to_999(rest))
    return " ".join(parts)


def _style(text: str) -> str:
    """
    Apply the grammar's post-composition rewrites in order.
    """
    text = re.sub(r"(?<=ற்று) ப", "ப்ப", text)
    text = re.sub(r"(?<=ற்று) த", "த்த", text)
    text = re.sub(rf"^{ONE} {THOUSAND}$", THOUSAND, text)
    text = re.sub(rf"^{ONE} {THOUSAND} ", f"{THOUSAND[:-2]}த்து ", text)
    text = re.sub(rf"^{ONE} (?={'|'.join(ORU_SCALES)})", f"{ORU} ", text)
    t = tables()
    for d in range(2, 10):
        word = t.digit[d]
        stem = word[:-1] + "ா"
        text = re.sub(rf"(^| ){word} {THOUSAND}$", rf"\1{stem}யிரம்", text)
        text = re.sub(rf"(^| ){word} {THOUSAND} ", rf"\1{stem}யிரத்து ", text)
    return text


ALTERNATIVE_SEPARATOR = "~"

# Exact tens 150-180 have two accepted forms; the grammar picks the fused one for
# Tamil-digit input and the spaced one for ASCII input.
FUSED_EXACT_TENS = {
    f"{HUNDRED_STEM} {tables().tens[50]}": "நூற்றைம்பது",
    f"{HUNDRED_STEM} {tables().tens[60]}": "நூற்றறுபது",
    f"{HUNDRED_STEM} {tables().tens[70]}": "நூற்றெழுபது",
    f"{HUNDRED_STEM} {tables().tens[80]}": "நூற்றெண்பது",
}


def with_alternatives(expected: str) -> str:
    """
    Join the accepted spoken variants of ``expected`` with ``~`` (golden-file convention).
    """
    fused = expected
    for spaced, joined in FUSED_EXACT_TENS.items():
        fused = fused.replace(spaced, joined)
    if fused == expected:
        return expected
    return f"{expected}{ALTERNATIVE_SEPARATOR}{fused}"


def digit_by_digit(digits: str) -> str:
    """
    Read a digit string one digit at a time (telephone style).
    """
    t = tables()
    return " ".join(ZERO if c == "0" else t.digit[int(c)] for c in to_ascii_digits(digits))


def cardinal(text: str) -> str:
    """
    Verbalize a written cardinal: digits, optional Indian/international commas, sign.

    Both Indian (``1,50,000``) and 3-digit (``150,000``) groupings read as ஒரு இலட்சம் ஐம்பது ஆயிரம்.
    """
    text = to_ascii_digits(text)
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if "," in text:
        if INDIAN_COMMA_RE.match(text) or INTL_COMMA_RE.match(text):
            words = _indian_groups(int(text.replace(",", "")))
        else:
            raise ValueError(f"unsupported comma pattern: {text!r}")
    elif len(text) == 2 and text[0] == "0":
        words = f"{ZERO} {_below_hundred(int(text[1]))}"
    elif (len(text) > 1 and text[0] == "0") or len(text) > 9:
        words = digit_by_digit(text)
    else:
        words = _indian_groups(int(text))
    words = _style(words)
    return f"{MINUS} {words}" if negative else words


def locative(text: str) -> str:
    """
    Case-suffixed cardinal, e.g. ``2024ல்`` -> இரண்டாயிரத்து இருபத்துநான்கில்.
    """
    words = cardinal(text)
    if words.endswith("ம்"):
        return words[:-2] + "த்தில்"
    if words.endswith("ு"):
        return words[:-1] + "ில்"
    raise ValueError(f"no locative form for {words!r}")


def _fraction_digits(digits: str) -> str:
    return digit_by_digit(digits)


def decimal(text: str, quantity: str | None = None) -> str:
    """
    Verbalize ``[-]INT.FRAC`` with digit-by-digit fraction, optional scale word.
    """
    text = to_ascii_digits(text)
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    integer, _, frac = text.partition(".")
    words = f"{cardinal(integer)} {POINT} {_fraction_digits(frac)}" if frac else cardinal(integer)
    if quantity:
        words = f"{words} {quantity}"
    return f"{MINUS} {words}" if negative else words


# --------------------------------------------------------------------------- others


def denominator_locative(den: int) -> str:
    """
    Locative (-இல்) form of a denominator, regular ``ு`` -> ``ில்`` morphology.
    """
    word = _up_to_999(den) if den < 1000 else cardinal(str(den))
    if word.endswith("நூறு") and word != "நூறு":
        return word[: -len("நூறு")] + "நூற்றில்"
    if word.endswith("ம்"):
        return word[:-2] + "த்தில்"
    if word.endswith("ி"):
        return word + "யில்"
    if not word.endswith("ு"):
        raise ValueError(f"no locative denominator for {den}")
    return word[:-1] + "ில்"


def fraction(text: str) -> str:
    """
    Verbalize ``[I ]N/D`` or ``[I]½``-style fractions, e.g. ``3/4`` -> நான்கில் மூன்று.
    """
    text = to_ascii_digits(text)
    integer = ""
    if text[-1] in VULGAR_FRACTIONS:
        num, den = VULGAR_FRACTIONS[text[-1]]
        integer = text[:-1].strip()
    else:
        integer, _, frac = text.rpartition(" ")
        num_s, den_s = frac.split("/")
        # Zero-led parts (15/06) are date fragments, not fractions.
        if den_s.startswith("0") or (num_s.startswith("0") and num_s != "0"):
            raise ValueError(f"not a fraction: {text!r}")
        num, den = int(num_s), int(den_s)
    words = f"{denominator_locative(den)} {cardinal(str(num))}"
    if integer:
        return f"{cardinal(integer)} {AND} {words}"
    return words


def date(text: str) -> str:
    """
    Verbalize numeric dates: DD-MM-YYYY, MM-DD-YYYY (day > 12), YYYY-MM-DD; sep ``-/.``.
    """
    t = tables()
    # One date uses one separator throughout, as the grammar requires: 15-06/2024 is not
    # a date, and the reference has no reading for the mixed shape.
    shape = re.fullmatch(r"(\d+)([-/.])(\d+)\2(\d+)", to_ascii_digits(text))
    if shape is None:
        raise ValueError(f"unsupported date shape: {text!r}")
    parts = [shape.group(1), shape.group(3), shape.group(4)]
    year_first = len(parts[0]) == 4
    year, first, second = parts if year_first else (parts[2], parts[0], parts[1])
    if len(year) != 4:
        raise ValueError(f"years must have four digits: {text!r}")
    month, day = (
        (first, second) if year_first or (int(first) <= 12 < int(second)) else (second, first)
    )
    if int(month) not in t.months or int(day) not in t.days:
        raise ValueError(f"invalid day or month: {text!r}")
    if year_first:
        return f"{cardinal(year)} {t.months[int(month)]} {t.days[int(day)]}"
    if int(first) <= 12 < int(second):
        return f"{t.months[int(month)]} {t.days[int(day)]} {cardinal(year)}"
    return f"{t.days[int(day)]} {t.months[int(month)]} {cardinal(year)}"


def time(text: str) -> str:
    """
    Verbalize ``H:MM[:SS]`` with an optional trailing ``மணிக்கு``.
    """
    t = tables()
    text = to_ascii_digits(text).replace("மணிக்கு", "").strip()
    parts = [int(p) for p in text.split(":")]
    words = f"{t.hours[parts[0]]} {HOUR}"
    if len(parts) > 1 and parts[1]:
        words += f" {t.minutes[parts[1]]} {MINUTE}"
    if len(parts) > 2 and parts[2]:
        words += f" {t.seconds[parts[2]]} {SECOND}"
    return words


def _one_as_oru(words: str) -> str:
    return ORU if words == ONE else words


def money(text: str) -> str:
    """
    Verbalize money with a prefix or suffix currency mark, e.g. ``₹1,250.50``.
    """
    t = tables()
    text = to_ascii_digits(text).replace("/-", "").strip()
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    match = re.match(r"^([^\d\s]+)\s*([\d,]+(?:\.\d+)?)$", text) or re.match(
        r"^([\d,]+(?:\.\d+)?)\s*(\S+)$", text
    )
    if match is None:
        raise ValueError(f"unsupported money shape: {text!r}")
    a, b = match.groups()
    symbol, amount = (a, b) if a in t.currency else (b, a)
    major = t.currency[symbol]
    integer, _, frac = amount.partition(".")
    integer_words = _one_as_oru(cardinal(integer))
    if frac and int(frac) == 0:
        # A .00 minor part is silent (₹1,999.00 -> ...ரூபாய்).
        frac = ""
    if not frac:
        words = f"{integer_words} {major}"
    elif len(frac) >= 3:
        # Three or more minor digits are not paise: a decimal amount (₹50.123).
        words = f"{cardinal(integer)} {POINT} {digit_by_digit(frac)} {major}"
    else:
        minor = int(frac) * 10 if len(frac) == 1 else int(frac)
        minor_words = _one_as_oru(cardinal(str(minor)))
        minor_unit = t.minor[major]
        if int(integer.replace(",", "")) == 0:
            words = f"{minor_words} {minor_unit}"
        else:
            words = f"{integer_words} {major} {minor_words} {minor_unit}"
    return f"{MINUS} {words}" if negative else words


def measure(text: str) -> str:
    """
    Verbalize ``[-]AMOUNT[ ]UNIT`` where UNIT is a key of ``measure/unit.tsv``.
    """
    t = tables()
    match = re.match(r"^(-?[\d,௦-௯]+(?:\.[\d௦-௯]+)?)\s*(.+)$", text)
    if match is None:
        raise ValueError(f"unsupported measure shape: {text!r}")
    amount, unit = match.groups()
    unit_words = t.units[unit]
    negative = amount.startswith("-")
    if negative:
        amount = amount[1:]
    amount_words = decimal(amount) if "." in amount else _one_as_oru(cardinal(amount))
    words = f"{amount_words} {unit_words}"
    return f"{MINUS} {words}" if negative else words


def ordinal(text: str) -> str:
    """
    Verbalize ``Nவது``, ``Nஆவது``, ``N-வது`` and ``Nஆம்`` ordinals.
    """
    match = re.match(r"^([\d௦-௯,]+)(-?வது|ஆவது|ஆம்)$", text)
    if match is None:
        raise ValueError(f"unsupported ordinal shape: {text!r}")
    number, suffix = match.groups()
    number = to_ascii_digits(number)
    if int(number.replace(",", "")) == 1:
        stem = FIRST_STEM
    else:
        words = cardinal(number)
        if not words.endswith(("ம்", "ு")):
            raise ValueError(f"no ordinal stem for {words!r}")
        stem = words[:-1] + "ா"
    return stem + ("ம்" if suffix == "ஆம்" else "வது")


def telephone(text: str) -> str:
    """
    Verbalize mobile (``+91 9876543210``) and landline (``044-28230000``) numbers.
    """
    text = to_ascii_digits(text)
    words = []
    if text.startswith("+"):
        code, _, rest = text[1:].partition(" ")
        if not rest:
            code, rest = code[:-10], code[-10:]
        words.append(f"{PLUS} {digit_by_digit(code)}")
        text = rest
    words.append(digit_by_digit(text.replace("-", "")))
    return " ".join(words)


def number_range(text: str) -> str:
    """
    Verbalize ``A-B`` as ``A முதல் B``.
    """
    lower, upper = text.split("-")
    return f"{cardinal(lower)} {RANGE_JOINER} {cardinal(upper)}"


def percent(text: str) -> str:
    """
    Verbalize ``N%`` / ``N.N%`` as ``N சதவீதம்``.
    """
    number = text.rstrip("%").strip()
    words = decimal(number) if "." in number else _one_as_oru(cardinal(number))
    return f"{words} {tables().symbols['%']}"


def equation(text: str) -> str:
    """
    Verbalize ``A×B=C`` / ``A÷B`` with the whitelist operator words.
    """
    t = tables()
    tokens = re.findall(r"[\d௦-௯]+|[×÷=]", text)
    return " ".join(cardinal(tok) if tok not in t.symbols else t.symbols[tok] for tok in tokens)


def abbreviation(text: str) -> str:
    """
    Expand a leading whitelist abbreviation, e.g. ``டாக். குமார்`` -> டாக்டர் குமார்.
    """
    t = tables()
    abbr, _, rest = text.partition(" ")
    return f"{t.abbreviations[abbr]} {rest}".strip()


def space_punctuation(text: str) -> str:
    """
    Detach sentence punctuation the way the word verbalizer does: ``வந்தான்.`` -> ``வந்தான் .``
    """
    return re.sub(r"(?<=\S)([.,!?])(?=\s|$)", r" \1", text)
