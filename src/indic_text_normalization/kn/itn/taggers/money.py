"""
Kannada currency words with their case endings, for the shared ITN money tagger.
"""

import pynini

from indic_text_normalization.core.itn_taggers.money import inflection_maps
from indic_text_normalization.kn.constants import CASE_SUFFIXES, LANG, SUFFIX_MARK
from indic_text_normalization.kn.morphology import suffix_sandhi

_SANDHI = suffix_sandhi()


def inflect(word: str, written: str) -> str:
    """
    The spoken form of ``word`` carrying the written suffix (ರೂಪಾಯಿ, ಕ್ಕೆ -> ರೂಪಾಯಿಗೆ).
    """
    return str(pynini.shortestpath((word + SUFFIX_MARK + written) @ _SANDHI).string())


def money_inflections() -> tuple[pynini.Fst, dict[str, pynini.Fst], pynini.Fst]:
    """
    The inflected currency, minor-unit and scaled-currency maps for the ITN money tagger.
    """
    return inflection_maps(LANG, CASE_SUFFIXES, inflect)
