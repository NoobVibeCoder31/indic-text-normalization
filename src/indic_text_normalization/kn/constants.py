"""
Kannada-specific constants: the language profile, sign and point words, suffixes.
"""

import pynini

from indic_text_normalization.core.profile import make_profile

LANG = "kn"

# Written register: a negative sign reads as the loanword ಮೈನಸ್, as in Kannada print.
MINUS_WORD = "ಮೈನಸ್"
PLUS_WORD = "ಪ್ಲಸ್"

# A range takes the ablative on its lower bound (ಹತ್ತರಿಂದ ಇಪ್ಪತ್ತು). The taggers place the
# bare word between the bounds; the sentence verbalizer glues it on with sandhi.
RANGE_WORD = "ರಿಂದ"

# Decimal point word (formal register), plus the spoken variants ITN accepts.
POINT_WORD = "ದಶಾಂಶ"
POINT_WORDS = (POINT_WORD, "ಪಾಯಿಂಟ್", "ಪಾಯಿಂಟು", "ಡೆಸಿಮಲ್")

# Marker placed between a noun and a case suffix before sandhi is applied; it is not a
# Kannada code point, so it can never appear in a spoken value.
SUFFIX_MARK = "␟"

# Case suffixes written glued to a digit (2024ರಲ್ಲಿ, 5ಕ್ಕೆ, 10ರಿಂದ); the written form already
# carries the -ರ augment a vowel-final number takes (ಐದು + ರಲ್ಲಿ -> ಐದರಲ್ಲಿ).
CASE_SUFFIXES = (
    "ರಲ್ಲಿ",
    "ರಲ್ಲೂ",
    "ರಲ್ಲೇ",
    "ರ",
    "ಕ್ಕೆ",
    "ಕ್ಕೂ",
    "ಕ್ಕೇ",
    "ಕ್ಕಾಗಿ",
    "ಕ್ಕಿಂತ",
    "ರಿಂದ",
    "ರಿಂದಲೇ",
    "ರಿಂದಲೂ",
    "ರಷ್ಟು",
    "ರಷ್ಟೇ",
    "ರವರೆಗೆ",
    "ರವರೆಗೂ",
    "ರೊಂದಿಗೆ",
    "ರಂತೆ",
    "ರೊಳಗೆ",
    "ರೊಳಗಾಗಿ",
)

# The written ordinal markers (5ನೇ, 5ನೆಯ, 5ನೆ).
ORDINAL_MARKERS = ("ನೇ", "ನೆಯ", "ನೆ")

# Kannada block U+0C80-U+0CFF; U+0CE6 KANNADA DIGIT ZERO opens the digit run.
PROFILE = make_profile(
    LANG,
    zero="೦",
    block=(0x0C80, 0x0D00),
    minus_word=MINUS_WORD,
    plus_word=PLUS_WORD,
    range_word=RANGE_WORD,
    point_word=POINT_WORD,
    point_words=POINT_WORDS,
    negative_words=("ಋಣ", "ನೆಗೆಟಿವ್"),
    case_suffixes=CASE_SUFFIXES,
)

KN_DIGIT = PROFILE.digits.digit
KN_LETTER = PROFILE.letter
# Consonant letters U+0C95 KANNADA LETTER KA .. U+0CB9 KANNADA LETTER HA (inherent -a).
KN_CONSONANT = pynini.union(*[chr(i) for i in range(0x0C95, 0x0CBA)]).optimize()
VIRAMA = "್"  # U+0CCD KANNADA SIGN VIRAMA
ANUSVARA = "ಂ"  # U+0C82 KANNADA SIGN ANUSVARA

# Vulgar fraction signs read as their everyday words; with an integer they fuse onto the
# lengthened final vowel (ಒಂದೂವರೆ, ಎರಡೂಕಾಲು, ಹತ್ತೂಮುಕ್ಕಾಲು).
VULGAR_WORDS = {"½": "ಅರ್ಧ", "¼": "ಕಾಲು", "¾": "ಮುಕ್ಕಾಲು"}
VULGAR_FUSED = {"½": "ೂವರೆ", "¼": "ೂಕಾಲು", "¾": "ೂಮುಕ್ಕಾಲು"}
AND_WORD = "ಮತ್ತು"
# Written part nouns after a fraction (3/4 ಭಾಗ) that the verbalizer speaks itself.
PART_NOUNS = ("ಭಾಗ",)
ITN_PART_NOUNS = ("ಭಾಗ", "ಭಾಗಗಳು")
BY_WORDS = ("ಬೈ",)
