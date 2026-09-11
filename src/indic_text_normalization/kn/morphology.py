"""
Kannada sandhi shared by the TN grammars: case suffixes on a noun, the ordinal stem and
the ablative a range's lower bound takes.
"""

import functools

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import NOT_QUOTE, SIGMA
from indic_text_normalization.kn.constants import (
    ANUSVARA,
    CASE_SUFFIXES,
    KN_CONSONANT,
    SUFFIX_MARK,
    VIRAMA,
)

ANY_WORD = pynini.closure(NOT_QUOTE, 1)

# Vowel signs that end a noun: -i/-e nouns glide with ಯ (ಕೋಟಿಯಲ್ಲಿ, ಗಂಟೆಗೆ), the others
# take -ದ (ಯೂರೋದಲ್ಲಿ, ಲಿರಾಗೆ).
GLIDE_SIGNS = ("ಿ", "ೀ", "ೆ", "ೇ", "ೈ")
OTHER_SIGNS = ("ಾ", "ೂ", "ೊ", "ೋ", "ೌ")
ZWNJ = "‌"  # U+200C ZERO WIDTH NON-JOINER keeps a suffix off a final conjunct (ಡಾಲರ್‌ಗೆ)


def _build_suffix_sandhi() -> pynini.Fst:
    """
    Build the sandhi rewrite chain; use ``suffix_sandhi``, which caches it.
    """
    mark = SUFFIX_MARK

    def rule(tau: pynini.Fst, left: pynini.Fst | str = "") -> pynini.Fst:
        return pynini.cdrewrite(tau, left, "", SIGMA)

    u_final = rule(pynutil.delete("ು" + mark))
    glide = rule(
        pynini.union(pynini.cross(mark + "ರ", "ಯ"), pynini.cross(mark + "ಕ್ಕ", "ಗ")),
        pynini.union(*GLIDE_SIGNS),
    )
    other_sign = rule(
        pynini.union(pynini.cross(mark + "ರ", "ದ"), pynini.cross(mark + "ಕ್ಕ", "ಗ")),
        pynini.union(*OTHER_SIGNS),
    )
    virama = rule(
        pynini.union(pynini.cross(mark + "ರ", ZWNJ + "ನ"), pynini.cross(mark + "ಕ್ಕ", ZWNJ + "ಗ")),
        VIRAMA,
    )
    anusvara = rule(
        pynini.union(pynini.cross(mark + "ರ", "ನ"), pynini.cross(mark + "ಕ್ಕ", "ಗ")), ANUSVARA
    )
    a_final = rule(pynini.cross(mark + "ರ", "ದ"), KN_CONSONANT)
    delete_mark = rule(pynutil.delete(mark))
    return (u_final @ glide @ other_sign @ virama @ anusvara @ a_final @ delete_mark).optimize()


@functools.cache
def _suffix_sandhi_cached() -> pynini.Fst:
    return _build_suffix_sandhi()


def suffix_sandhi() -> pynini.Fst:
    """
    Join a noun and the written case suffix after ``SUFFIX_MARK``.

    -ು: ಐದು + ರಲ್ಲಿ -> ಐದರಲ್ಲಿ, ಐದು + ಕ್ಕೆ -> ಐದಕ್ಕೆ; -ಅ: ಸಾವಿರ + ರಲ್ಲಿ -> ಸಾವಿರದಲ್ಲಿ, ಸಾವಿರ + ಕ್ಕೆ
    -> ಸಾವಿರಕ್ಕೆ; -ಿ/-ೆ: ಕೋಟಿ + ರಲ್ಲಿ -> ಕೋಟಿಯಲ್ಲಿ, ಗಂಟೆ + ಕ್ಕೆ -> ಗಂಟೆಗೆ; -್: ಡಾಲರ್ + ಕ್ಕೆ ->
    ಡಾಲರ್‌ಗೆ; -ಂ: ಕಿಲೋಗ್ರಾಂ + ಕ್ಕೆ -> ಕಿಲೋಗ್ರಾಂಗೆ.
    """
    return _suffix_sandhi_cached().copy()


def written_suffix() -> pynini.Fst:
    """
    A written glued suffix to the marker plus itself (ರಲ್ಲಿ -> ␟ರಲ್ಲಿ).
    """
    return pynini.string_map([(s, SUFFIX_MARK + s) for s in CASE_SUFFIXES]).optimize()


def optional_suffix_field() -> pynini.Fst:
    """
    Consume an optional ``suffix: "..."`` field, emitting the marked suffix.
    """
    return pynini.closure(
        pynutil.delete(pynini.closure(" ", 0, 1))
        + pynutil.delete('suffix: "')
        + written_suffix()
        + pynutil.delete('"'),
        0,
        1,
    )


def ordinal_stem() -> pynini.Fst:
    """
    Stem a number word takes before the ordinal marker -ನೇ: ಐದು -> ಐದನೇ, ಸಾವಿರ -> ಸಾವಿರನೇ.
    """
    return (SIGMA + pynini.union(pynutil.delete("ು"), pynini.difference(NOT_QUOTE, "ು"))).optimize()


def range_sandhi() -> pynini.Fst:
    """
    Glue the range word ರಿಂದ onto the word before it with the ablative sandhi:
    ಹತ್ತು ರಿಂದ -> ಹತ್ತರಿಂದ, ಸಾವಿರ ರಿಂದ -> ಸಾವಿರದಿಂದ, ಕೋಟಿ ರಿಂದ -> ಕೋಟಿಯಿಂದ, ಡಾಲರ್ ರಿಂದ -> ಡಾಲರ್‌ನಿಂದ.
    """
    word = " ರಿಂದ"

    def rule(tau: pynini.Fst, left: pynini.Fst | str) -> pynini.Fst:
        return pynini.cdrewrite(tau, left, "", SIGMA)

    return (
        rule(pynini.cross("ು" + word, "ರಿಂದ"), "")
        @ rule(pynini.cross(word, "ಯಿಂದ"), pynini.union(*GLIDE_SIGNS))
        @ rule(pynini.cross(word, "ದಿಂದ"), pynini.union(*OTHER_SIGNS))
        @ rule(pynini.cross(word, ZWNJ + "ನಿಂದ"), VIRAMA)
        @ rule(pynini.cross(word, "ನಿಂದ"), ANUSVARA)
        @ rule(pynini.cross(word, "ದಿಂದ"), KN_CONSONANT)
    ).optimize()
