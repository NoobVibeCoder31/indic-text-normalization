"""
Malayalam currency words with their case endings, for the shared ITN money tagger.

A suffix changes shape on the noun it follows (രൂപയ്ക്ക്, പൈസയിൽ, കോടിക്ക്), so the spoken
inflected forms are enumerated from the same sandhi the TN verbalizers apply.
"""

import pynini

from indic_text_normalization.core.itn_taggers.money import inflection_maps
from indic_text_normalization.ml.constants import LANG, SUFFIX_MARK, WRITTEN_SUFFIXES
from indic_text_normalization.ml.morphology import suffix_sandhi

_SANDHI = suffix_sandhi()


def inflect(word: str, written: str) -> str:
    """
    The spoken form of ``word`` carrying the written suffix (രൂപ, ന് -> രൂപയ്ക്ക്).
    """
    spoken = WRITTEN_SUFFIXES[written]
    return str(pynini.shortestpath((word + SUFFIX_MARK + spoken) @ _SANDHI).string())


def canonical_written_suffixes() -> list[str]:
    """
    The spelling ITN writes for each spoken suffix: the first listed.
    """
    first: dict[str, str] = {}
    for written, spoken in WRITTEN_SUFFIXES.items():
        first.setdefault(spoken, written)
    return list(first.values())


def money_inflections() -> tuple[pynini.Fst, dict[str, pynini.Fst], pynini.Fst]:
    """
    The inflected currency, minor-unit and scaled-currency maps for the ITN money tagger.
    """
    return inflection_maps(LANG, canonical_written_suffixes(), inflect)
