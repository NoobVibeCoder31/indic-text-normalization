"""
Kannada spoken-number normalization for ITN: the variant pre-map.
"""

import pynini

from indic_text_normalization.core.graph_utils import SIGMA

# Spelling variants ITN accepts and the form the TN grammar emits.
VARIANTS = [
    ("ಒಂಭತ್ತು", "ಒಂಬತ್ತು"),
    ("ಹತ್ತೊಂಭತ್ತು", "ಹತ್ತೊಂಬತ್ತು"),
    ("ಎಂಬತ್ತು", "ಎಂಭತ್ತು"),
    ("ತೊಂಭತ್ತು", "ತೊಂಬತ್ತು"),
    ("ನಲ್ವತ್ತು", "ನಲವತ್ತು"),
    ("ಹದಿನೈದು", "ಹದಿನೈದು"),
    ("ಸಾವಿರದ", "ಸಾವಿರದ"),
    ("ಶೂನ್ಯ", "ಸೊನ್ನೆ"),
    ("ಜೀರೋ", "ಸೊನ್ನೆ"),
    ("ಝೀರೋ", "ಸೊನ್ನೆ"),
    ("ಒಂದು ನೂರು", "ನೂರು"),
]
# Fused tens and a vowel-initial unit are undone by the tens stem context below.
TENS = ("ಇಪ್ಪತ್ತು", "ಮೂವತ್ತು", "ನಲವತ್ತು", "ಐವತ್ತು", "ಅರವತ್ತು", "ಎಪ್ಪತ್ತು", "ಎಂಭತ್ತು", "ತೊಂಬತ್ತು")
VOWEL_SIGNS = {"ಒ": "ೊ", "ಎ": "ೆ", "ಐ": "ೈ", "ಆ": "ಾ", "ಏ": "ೇ"}


def spoken_pre_map() -> pynini.Fst:
    """
    Normalize spoken and colloquial number phrasing to the forms the TN grammar emits.
    """
    edge = pynini.union("[BOS]", " ")
    right = pynini.union("[EOS]", " ")
    variants = pynini.cdrewrite(
        pynini.union(*[pynini.cross(a, b) for a, b in VARIANTS]), edge, right, SIGMA
    )
    # Spaced tens and units fuse back: ಇಪ್ಪತ್ತು ಮೂರು -> ಇಪ್ಪತ್ತಮೂರು, ಇಪ್ಪತ್ತು ಒಂದು -> ಇಪ್ಪತ್ತೊಂದು.
    stems = pynini.union(*[t[:-1] for t in TENS])
    fuse_units = pynini.cdrewrite(
        pynini.union(
            *[pynini.cross("ು " + v, sign) for v, sign in VOWEL_SIGNS.items()],
            pynini.cross("ು ಮ", "ಮ"),
            pynini.cross("ು ನ", "ನ"),
        ),
        stems,
        pynini.union("ಂ", "ರ", "ೂ", "ಾ", "ದ", "ಳ", "ಟ", "ಬ"),
        SIGMA,
    )
    # A U+200C ZERO WIDTH NON-JOINER typed inside a loanword is a typing artefact.
    zwnj = pynini.cdrewrite(pynini.cross("್‌", "್"), "", "", SIGMA)
    return (variants @ fuse_units @ zwnj).optimize()
