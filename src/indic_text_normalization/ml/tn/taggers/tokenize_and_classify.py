"""
Malayalam TN sentence classifier: the shared taggers bound to the Malayalam profile.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA
from indic_text_normalization.core.tn_taggers.classify import TnClassifyFst
from indic_text_normalization.core.tn_taggers.date import DateFst
from indic_text_normalization.core.tn_taggers.decimal import DecimalFst
from indic_text_normalization.core.tn_taggers.fraction import FractionFst
from indic_text_normalization.core.tn_taggers.measure import MeasureFst
from indic_text_normalization.core.tn_taggers.money import MoneyFst
from indic_text_normalization.core.tn_taggers.ordinal import OrdinalFst
from indic_text_normalization.core.tn_taggers.prepass import PrePassWords, build_pre_pass
from indic_text_normalization.core.tn_taggers.range import RangeFst
from indic_text_normalization.core.tn_taggers.telephone import TelephoneFst
from indic_text_normalization.core.tn_taggers.time import TimeFst
from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.ml.constants import (
    LANG,
    PART_NOUNS,
    PROFILE,
    SUFFIX_MARK,
    VIRAMA,
    VULGAR_FUSED,
    VULGAR_WORDS,
    WRITTEN_SUFFIXES,
)
from indic_text_normalization.ml.morphology import SCALE_WORDS, suffix_sandhi
from indic_text_normalization.ml.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.ml.tn.taggers.time import TIME_WORDS

# A case suffix written on % (10%ൽ): ശതമാനം is an -ം noun (ശതമാനത്തിൽ, ശതമാനവും).
PERCENT_SUFFIXES = (
    ("%ൽ", " ശതമാനത്തിൽ"),
    ("%ിൽ", " ശതമാനത്തിൽ"),
    ("%ലെ", " ശതമാനത്തിലെ"),
    ("%ന്", " ശതമാനത്തിന്"),
    ("%ിന്", " ശതമാനത്തിന്"),
    ("%ും", " ശതമാനവും"),
    ("%ഉം", " ശതമാനവും"),
    ("%ായി", " ശതമാനമായി"),
    ("%ആയി", " ശതമാനമായി"),
    ("%ോളം", " ശതമാനത്തോളം"),
    ("%ഓളം", " ശതമാനത്തോളം"),
    ("%ോടെ", " ശതമാനത്തോടെ"),
    ("%ഓടെ", " ശതമാനത്തോടെ"),
    ("%ന്റെ", " ശതമാനത്തിന്റെ"),
)

# Symbols the whitelist speaks are always their own token, so the first pass already
# speaks them whether or not they were glued (5#, അ%, ₹* ...).
SPOKEN_SYMBOLS = "#*&^%|~©®™§√∛∞≠≈≤≥±→←↔↑↓"


def _mixed_vulgar(cardinal: CardinalFst) -> pynini.Fst:
    """
    1½ -> ഒന്നര, 2¼ -> രണ്ടേകാൽ, 10¾ -> പത്തേമുക്കാൽ: the sign fuses onto a virama-final integer.
    """
    stem = cardinal.final_graph @ (SIGMA + pynutil.delete(VIRAMA))
    optional_space = pynutil.delete(pynini.closure(" ", 0, 1))
    signs = pynini.union(*[pynini.cross(s, w) for s, w in VULGAR_FUSED.items()])
    return stem + optional_space + signs


def _inflected_quantity() -> pynini.Fst:
    """
    A scale word with a case ending (കോടിക്ക്, ലക്ഷത്തിൽ) to the bare word plus the written
    suffix it stands for, in the form the money tagger's suffix field takes.
    """
    sandhi = suffix_sandhi()
    canonical: dict[str, str] = {}
    for written, spoken in WRITTEN_SUFFIXES.items():
        canonical.setdefault(spoken, written)
    pairs = []
    for word in SCALE_WORDS:
        for spoken, written in canonical.items():
            inflected = pynini.shortestpath((word + SUFFIX_MARK + spoken) @ sandhi).string()
            pairs.append((inflected, f'{word}" suffix: "{written}'))
    return pynini.string_map(pairs).optimize()


def count_nouns() -> tuple[str, ...]:
    """
    Nouns a numeral counts (numbers/count_nouns.tsv) plus the unit words.
    """
    nouns = [row[0] for row in load_labels(data_path(LANG, "numbers/count_nouns.tsv"))]
    units = load_labels(data_path(LANG, "measure/unit.tsv"), min_fields=2)
    return tuple(dict.fromkeys(nouns + [row[1] for row in units]))


class ClassifyFst(TnClassifyFst):
    """
    Composes all Malayalam TN taggers into a single sentence classifier.
    """

    def __init__(self, deterministic: bool = True) -> None:
        cardinal = CardinalFst(deterministic=deterministic)
        decimal = DecimalFst(cardinal, deterministic=deterministic)
        pre_pass = build_pre_pass(
            PROFILE,
            PrePassWords(
                spoken_symbols=SPOKEN_SYMBOLS,
                percent_suffixes=PERCENT_SUFFIXES,
                division="ഹരണം",
                count_nouns=count_nouns(),
            ),
            known_suffixes=cardinal.known_suffixes,
        )
        super().__init__(
            PROFILE,
            cardinal=cardinal,
            decimal=decimal,
            fraction=FractionFst(
                cardinal,
                vulgar_words=VULGAR_WORDS,
                and_word=None,
                part_nouns=PART_NOUNS,
                mixed_vulgar=_mixed_vulgar(cardinal),
                deterministic=deterministic,
            ),
            measure=MeasureFst(cardinal, decimal, deterministic=deterministic),
            time=TimeFst(PROFILE, TIME_WORDS, deterministic=deterministic),
            date=DateFst(cardinal, deterministic=deterministic),
            money=MoneyFst(
                cardinal, inflected_quantity=_inflected_quantity(), deterministic=deterministic
            ),
            telephone=TelephoneFst(cardinal, deterministic=deterministic),
            ordinal=OrdinalFst(cardinal, deterministic=deterministic),
            range=RangeFst(cardinal, deterministic=deterministic),
            pre_pass=pre_pass,
            deterministic=deterministic,
        )
