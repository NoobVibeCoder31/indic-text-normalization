"""
Malayalam spoken-number normalization for ITN: the variant pre-map.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA

# Spelling variants ITN accepts and the form the TN grammar emits.
VARIANTS = [
    ("അമ്പത്", "അൻപത്"),
    ("അമ്പത്തി", "അൻപത്തി"),
    ("ഒമ്പത്", "ഒൻപത്"),
    ("പത്തൊമ്പത്", "പത്തൊൻപത്"),
    ("എണ്പത്", "എൺപത്"),
    ("എണ്പത്തി", "എൺപത്തി"),
    ("നാല്പത്", "നാൽപത്"),
    ("നാല്പത്തി", "നാൽപത്തി"),
    ("നാലു", "നാല്"),
    ("ഒന്നു", "ഒന്ന്"),
    ("രണ്ടു", "രണ്ട്"),
    ("മൂന്നു", "മൂന്ന്"),
    ("അഞ്ചു", "അഞ്ച്"),
    ("ആറു", "ആറ്"),
    ("ഏഴു", "ഏഴ്"),
    ("എട്ടു", "എട്ട്"),
    ("പത്തു", "പത്ത്"),
    ("നൂറു", "നൂറ്"),
    ("മുന്നൂറ്", "മുന്നൂറ്"),
    ("ആയിരത്തൊന്ന്", "ആയിരത്തി ഒന്ന്"),
    ("ലക്ഷ", "ലക്ഷം"),
    ("സീറോ", "പൂജ്യം"),
    ("സിറോ", "പൂജ്യം"),
]
# Variants inside a word: മൂന്നായിരം for മൂവായിരം (also പതിമൂന്നായിരം).
INNER_VARIANTS = [("മൂന്നായിരം", "മൂവായിരം")]

# Old-style chillus (consonant + virama + U+200D ZERO WIDTH JOINER) and the atomic chillu;
# a U+200C ZERO WIDTH NON-JOINER typed after a chillu or virama is a typing artefact.
OLD_CHILLU = [("ന്‍", "ൻ"), ("ല്‍", "ൽ"), ("ര്‍", "ർ"), ("ള്‍", "ൾ"), ("ണ്‍", "ൺ")]

TENS_LINK = (
    "ഇരുപത്തി",
    "മുപ്പത്തി",
    "നാൽപത്തി",
    "അൻപത്തി",
    "അറുപത്തി",
    "എഴുപത്തി",
    "എൺപത്തി",
    "തൊണ്ണൂറ്റി",
)


def spoken_pre_map() -> pynini.Fst:
    """
    Normalize spoken and colloquial number phrasing to the forms the TN grammar emits.
    """
    edge = pynini.union("[BOS]", " ")
    right = pynini.union("[EOS]", " ")
    chillu = pynini.cdrewrite(
        pynini.union(*[pynini.cross(a, b) for a, b in OLD_CHILLU]), "", "", SIGMA
    ) @ pynini.cdrewrite(
        pynini.union(*[pynini.cross(c + "\u200c", c) for c in ("ൻ", "ൽ", "ർ", "ൾ", "ൺ", "്")]),
        "",
        "",
        SIGMA,
    )
    variants = pynini.cdrewrite(
        pynini.union(*[pynini.cross(a, b) for a, b in VARIANTS]), edge, right, SIGMA
    ) @ pynini.cdrewrite(
        pynini.union(*[pynini.cross(a, b) for a, b in INNER_VARIANTS]), "", "", SIGMA
    )
    # Spaced tens and units fuse back: ഇരുപത്തി മൂന്ന് -> ഇരുപത്തിമൂന്ന്, ഇരുപത്തി ഒന്ന് -> ഇരുപത്തിയൊന്ന്.
    fuse_units = pynini.cdrewrite(
        pynini.union(
            pynini.cross(" ഒ", "യൊ"),
            pynini.cross(" അ", "യ"),
            pynini.cross(" ആ", "യാ"),
            pynini.cross(" ഏ", "യേ"),
            pynini.cross(" എ", "യെ"),
            pynutil.delete(" "),
        ),
        pynini.union(*TENS_LINK),
        pynini.union("ഒ", "അ", "ആ", "ഏ", "എ", "ര", "മ", "ന"),
        SIGMA,
    )
    return (chillu @ variants @ fuse_units).optimize()
