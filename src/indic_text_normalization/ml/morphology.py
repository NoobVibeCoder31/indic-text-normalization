"""
Malayalam sandhi shared by the TN grammars: case suffixes on a noun, the counting ഒരു,
the glide and gemination that join a number word to a linking form, and the fused
thousands (അഞ്ച് + ആയിരം -> അഞ്ചായിരം).
"""

import functools

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import CHAR, NOT_QUOTE, SIGMA
from indic_text_normalization.ml.constants import (
    ANUSVARA,
    ML_CONSONANT,
    POINT_WORD,
    SUFFIX_MARK,
    VIRAMA,
    WRITTEN_SUFFIXES,
)

ONE = "ഒന്ന്"
ORU = "ഒരു"
ONE_AS_ORU = pynini.cross(ONE, ORU)
NOT_ONE = pynini.difference(pynini.closure(NOT_QUOTE, 1), pynini.accep(ONE)).optimize()

# Native scale words a counting ഒന്ന് precedes as ഒരു (ഒന്ന് ലക്ഷം -> ഒരു ലക്ഷം).
SCALE_WORDS = ("ആയിരം", "ലക്ഷം", "കോടി", "മില്യൻ", "ബില്യൻ", "ട്രില്യൻ")

# Independent vowel -> the sign it becomes after a glide യ.
VOWEL_SIGNS = {"അ": "", "ആ": "ാ", "ഇ": "ി", "ഈ": "ീ", "ഉ": "ു", "ഊ": "ൂ", "എ": "െ", "ഏ": "േ", "ഒ": "ൊ", "ഓ": "ോ", "ഐ": "ൈ", "ഔ": "ൗ"}  # fmt: skip
# Consonants doubled after a linking -ി (നൂറ്റി + പത്ത് -> നൂറ്റിപ്പത്ത്).
GEMINATING = ("പ", "ത", "ക", "ച", "ട")
# Malayalam chillu letters and the consonant each stands for.
CHILLU = {"ർ": "റ", "ൻ": "ന", "ൺ": "ണ", "ൽ": "ല", "ൾ": "ള"}
# Loanwords whose final -ം is a real m and inflects as such (ഗ്രാമിൽ, not ഗ്രാത്തിൽ).
LOAN_ANUSVARA = ("ഗ്രാം", "ഓം", "ടീം", "ഫോം")


def join_after_i() -> pynini.Fst:
    """
    Sandhi on a number word that follows a linking form ending in -ി: a glide before a
    vowel (ഒന്ന് -> യൊന്ന്, അഞ്ച് -> യഞ്ച്), a doubled പ/ത (പത്ത് -> പ്പത്ത്), else unchanged.
    """
    first = pynini.union(
        *[pynini.cross(v, "യ" + sign) for v, sign in VOWEL_SIGNS.items()],
        *[pynini.cross(c, c + VIRAMA + c) for c in GEMINATING],
        pynini.difference(CHAR, pynini.union(*VOWEL_SIGNS, *GEMINATING)),
    )
    return (first + SIGMA).optimize()


def linking_form() -> pynini.Fst:
    """
    The linking form of a scale word before a remainder: ആയിരം -> ആയിരത്തി, ലക്ഷം -> ലക്ഷത്തി.
    """
    return (SIGMA + pynini.cross(ANUSVARA, "ത്തി")).optimize()


def ordinal_stem() -> pynini.Fst:
    """
    Stem a number word takes before the ordinal marker -ാം: അഞ്ച് -> അഞ്ചാം, ആയിരം -> ആയിരാം,
    കോടി -> കോടിയാം.
    """
    return (
        SIGMA
        + pynini.union(pynutil.delete(VIRAMA), pynutil.delete(ANUSVARA), pynini.cross("ി", "ിയ"))
    ).optimize()


def _build_suffix_sandhi() -> pynini.Fst:
    """
    Build the sandhi rewrite chain; use ``suffix_sandhi``, which caches it.
    """
    mark = SUFFIX_MARK
    # A suffix closes the value, so a dative/genitive rule must see its end.
    end = pynini.union("[EOS]", " ")

    def rule(
        tau: pynini.Fst, left: pynini.Fst | str = "", right: pynini.Fst | str = ""
    ) -> pynini.Fst:
        return pynini.cdrewrite(tau, left, right, SIGMA)

    loan = rule(
        pynini.union(
            *[pynini.cross(w + mark, w[:-1] + "മ" + VIRAMA + mark) for w in LOAN_ANUSVARA]
        ),
        "",
        "",
    )
    anusvara = rule(
        pynini.union(
            pynini.cross(ANUSVARA + mark + "ി", "ത്തി"),
            pynini.cross(ANUSVARA + mark + "ും", "വും"),
            pynini.cross(ANUSVARA + mark + "ോ", "ത്തോ"),
            pynini.cross(ANUSVARA + mark + "ാ", "മാ"),
        )
    )
    dative_i = rule(
        pynini.union(
            pynini.cross("ി" + mark + "ിന്", "ിക്ക്"),
            pynini.cross("ി" + mark + "ിനും", "ിക്കും"),
            pynini.cross("ി" + mark + "ിന്റെ", "ിയുടെ"),
            pynini.cross("ോ" + mark + "ിന്", "ോയ്ക്ക്"),
            pynini.cross("ോ" + mark + "ിനും", "ോയ്ക്കും"),
            pynini.cross("ോ" + mark + "ിന്റെ", "ോയുടെ"),
        ),
        "",
        end,
    )
    glide_i = rule(pynini.cross(mark, "യ"), pynini.union("ി", "ോ"))
    dative_a = rule(
        pynini.union(
            pynini.cross(mark + "ിന്", "യ്ക്ക്"),
            pynini.cross(mark + "ിനും", "യ്ക്കും"),
            pynini.cross(mark + "ിന്റെ", "യുടെ"),
        ),
        ML_CONSONANT,
        end,
    )
    glide_a = rule(pynini.cross(mark, "യ"), ML_CONSONANT)
    virama = rule(pynutil.delete(VIRAMA + mark))
    chillu = rule(pynini.union(*[pynini.cross(c + mark, base) for c, base in CHILLU.items()]))
    delete_mark = rule(pynutil.delete(mark))
    return (
        loan @ anusvara @ dative_i @ glide_i @ dative_a @ glide_a @ virama @ chillu @ delete_mark
    ).optimize()


def written_suffix_to_spoken() -> pynini.Fst:
    """
    A written glued suffix to the marker plus its canonical spoken suffix (ൽ -> ␟ിൽ).
    """
    return pynini.string_map(
        [(written, SUFFIX_MARK + spoken) for written, spoken in WRITTEN_SUFFIXES.items()]
    ).optimize()


def canonical_written_suffixes() -> pynini.Fst:
    """
    The same map restricted to the spelling ITN writes for each spoken suffix.
    """
    first: dict[str, str] = {}
    for written, spoken in WRITTEN_SUFFIXES.items():
        first.setdefault(spoken, written)
    return pynini.string_map(
        [(written, SUFFIX_MARK + spoken) for spoken, written in first.items()]
    ).optimize()


def optional_suffix_field() -> pynini.Fst:
    """
    Consume an optional ``suffix: "..."`` field, emitting the marked canonical suffix.
    """
    return pynini.closure(
        pynutil.delete(pynini.closure(" ", 0, 1))
        + pynutil.delete('suffix: "')
        + written_suffix_to_spoken()
        + pynutil.delete('"'),
        0,
        1,
    )


def one_before_scale() -> pynini.Fst:
    """
    A counting ഒന്ന് heading a scale phrase reads as ഒരു (ഒന്ന് ലക്ഷം -> ഒരു ലക്ഷം), but
    not before a decimal point (ഒന്ന് ദശാംശം അഞ്ച് ലക്ഷം keeps ഒന്ന്).
    """
    return pynini.cdrewrite(ONE_AS_ORU, "[BOS]", " " + pynini.union(*SCALE_WORDS), SIGMA).optimize()


def fuse_thousand() -> pynini.Fst:
    """
    A number before ആയിരം fuses with it: അഞ്ച് ആയിരം -> അഞ്ചായിരം, മൂന്ന് ആയിരം -> മൂവായിരം,
    പത്ത് ആയിരം -> പതിനായിരം, ഇരുപത് ആയിരം -> ഇരുപതിനായിരം, ഒരു ആയിരം -> ആയിരം.
    """
    end = pynini.union("[EOS]", " ")
    rules = [
        pynini.cross("ഒരു ആയിരം", "ആയിരം"),
        pynini.cross("മൂന്ന് ആയിരം", "മൂവായിരം"),
        pynini.cross("പത്ത് ആയിരം", "പതിനായിരം"),
        pynini.cross("പത് ആയിരം", "പതിനായിരം"),
        pynini.cross("ൂറ് ആയിരം", "ൂറായിരം"),
        pynini.cross(VIRAMA + " ആയിരം", "ായിരം"),
    ]
    graph = pynini.cdrewrite(pynini.accep(""), "", "", SIGMA)
    for tau in rules:
        graph @= pynini.cdrewrite(tau, "", end, SIGMA)
    return graph.optimize()


NBSP_TO_SPACE = pynini.cdrewrite(pynini.cross(" ", " "), "", "", SIGMA).optimize()
NOT_POINT_PHRASE = pynini.difference(
    pynini.closure(NOT_QUOTE, 1), SIGMA + POINT_WORD + SIGMA
).optimize()


@functools.cache
def _suffix_sandhi_cached() -> pynini.Fst:
    return _build_suffix_sandhi()


def suffix_sandhi() -> pynini.Fst:
    """
    Join a noun and the canonical case suffix after ``SUFFIX_MARK``.

    virama-final: അഞ്ച് + ിൽ -> അഞ്ചിൽ, അഞ്ച് + ും -> അഞ്ചും; -ം: ആയിരം + ിൽ -> ആയിരത്തിൽ,
    + ും -> ആയിരവും, + ായി -> ആയിരമായി; -ി: കോടി + ിൽ -> കോടിയിൽ, + ിന് -> കോടിക്ക്;
    -അ: രൂപ + ിൽ -> രൂപയിൽ, + ിന് -> രൂപയ്ക്ക്; chillu: ഡോളർ + ിൽ -> ഡോളറിൽ.
    """
    return _suffix_sandhi_cached().copy()
