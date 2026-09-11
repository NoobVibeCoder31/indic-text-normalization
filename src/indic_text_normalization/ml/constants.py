"""
Malayalam-specific constants: the language profile, sign and point words, suffixes.
"""

import pynini

from indic_text_normalization.core.profile import make_profile

LANG = "ml"

# Written register: a negative sign reads as the loanword മൈനസ്, as in Malayalam print.
MINUS_WORD = "മൈനസ്"
MINUS = pynini.union(" മൈനസ് ").optimize()
PLUS_WORD = "പ്ലസ്"

# A range reads പത്ത് മുതൽ ഇരുപത് വരെ: a word between the bounds and one after them.
RANGE_WORD = "മുതൽ"
RANGE_SUFFIX = "വരെ"

# Decimal point word (formal register), plus the spoken variants ITN accepts.
POINT_WORD = "ദശാംശം"
POINT_WORDS = (POINT_WORD, "പോയിന്റ്", "പോയിന്‍റ്", "പോയന്റ്", "ഡെസിമൽ")

# Marker placed between a noun and a case suffix before sandhi is applied; it is not a
# Malayalam code point, so it can never appear in a spoken value.
SUFFIX_MARK = "␟"

# Written case suffixes glued to a digit (2024ൽ, 15ന്, 5ഉം) and the spoken suffix each
# stands for before sandhi (2024ൽ -> ...നാലിൽ, 15ന് -> പതിനഞ്ചിന്). The first spelling of
# each spoken suffix is the one ITN writes: a vowel-initial suffix takes its independent
# vowel after a digit (5ഉം, 5ഓടെ), since a vowel sign cannot attach to a digit.
WRITTEN_SUFFIXES: dict[str, str] = {
    "ൽ": "ിൽ",
    "ിൽ": "ിൽ",
    "ലെ": "ിലെ",
    "ിലെ": "ിലെ",
    "ന്": "ിന്",
    "ിന്": "ിന്",
    "നും": "ിനും",
    "ിനും": "ിനും",
    "ലേക്ക്": "ിലേക്ക്",
    "ിലേക്ക്": "ിലേക്ക്",
    "ന്റെ": "ിന്റെ",
    "ിന്റെ": "ിന്റെ",
    "ൻറെ": "ിന്റെ",
    "ഉം": "ും",
    "ും": "ും",
    "ഓടെ": "ോടെ",
    "ോടെ": "ോടെ",
    "ഓളം": "ോളം",
    "ോളം": "ോളം",
    "ആയി": "ായി",
    "ായി": "ായി",
    "ലും": "ിലും",
    "ിലും": "ിലും",
}
CASE_SUFFIXES = tuple(WRITTEN_SUFFIXES)
CANONICAL_SUFFIXES = tuple(dict.fromkeys(WRITTEN_SUFFIXES.values()))

# The written ordinal marker -ാം (5-ാം, 5ാം) and its inflected tails (5-ാമത്തെ); the
# independent-vowel spelling ആം is accepted too.
ORDINAL_MARKERS = ("ാം", "ാമത്", "ാമത്തെ", "ാമതായി", "ാമത്തേത്", "ാമൻ", "ാമതും", "ാമതെ")
ORDINAL_MARKER_VARIANTS = {m: "ആ" + m[1:] for m in ORDINAL_MARKERS}

# Malayalam block U+0D00-U+0D7F; U+0D66 MALAYALAM DIGIT ZERO opens the digit run.
PROFILE = make_profile(
    LANG,
    zero="൦",
    block=(0x0D00, 0x0D80),
    minus_word=MINUS_WORD,
    plus_word=PLUS_WORD,
    range_word=RANGE_WORD,
    range_suffix=RANGE_SUFFIX,
    point_word=POINT_WORD,
    point_words=POINT_WORDS,
    negative_words=("ന്യൂന", "ഋണ", "നെഗറ്റീവ്"),
    case_suffixes=CASE_SUFFIXES,
    counting_one="ഒരു",
)

ML_DIGIT = PROFILE.digits.digit
ML_LETTER = PROFILE.letter
# Consonant letters U+0D15 MALAYALAM LETTER KA .. U+0D39 MALAYALAM LETTER HA (inherent -a).
ML_CONSONANT = pynini.union(*[chr(i) for i in range(0x0D15, 0x0D3A)]).optimize()
VIRAMA = "്"  # U+0D4D MALAYALAM SIGN VIRAMA
ANUSVARA = "ം"  # U+0D02 MALAYALAM SIGN ANUSVARA

# Vulgar fraction signs read as their everyday words; with an integer they fuse
# (ഒന്നര, രണ്ടേകാൽ, പത്തേമുക്കാൽ).
VULGAR_WORDS = {"½": "അര", "¼": "കാൽ", "¾": "മുക്കാൽ"}
VULGAR_FUSED = {"½": "ര", "¼": "േകാൽ", "¾": "േമുക്കാൽ"}
# Written part nouns after a fraction (3/4 ഭാഗം) that the verbalizer speaks itself.
PART_NOUNS = ("ഭാഗം",)
BY_WORDS = ("ബൈ",)
