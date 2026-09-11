"""
Hindi-specific constants: the language profile, sign and point words, ordinal markers.
"""

from indic_text_normalization.core.profile import make_profile

LANG = "hi"

# Written register: a negative sign reads as the loanword माइनस, as in Hindi print; ITN
# also accepts the textbook ऋण.
MINUS_WORD = "माइनस"
PLUS_WORD = "प्लस"

# Spoken between the bounds of a range (10-20 -> दस से बीस).
RANGE_WORD = "से"

# Decimal point word (formal register), plus the spoken variants ITN accepts.
POINT_WORD = "दशमलव"
POINT_WORDS = (POINT_WORD, "पॉइंट", "पॉइन्ट", "पाइंट", "बिंदु", "डेसिमल")

# Hindi postpositions are separate words, so nothing but an ordinal marker is written
# glued to a digit.
CASE_SUFFIXES: tuple[str, ...] = ()

# Ordinal markers written after a digit, by gender and case: 5वाँ (m), 5वीं (f), 5वें (obl).
# The anusvara spellings (5वां, 5वे) are accepted too; the chandrabindu is written back.
ORDINAL_MARKERS = {"वाँ": "वाँ", "वां": "वाँ", "वीं": "वीं", "वी": "वीं", "वें": "वें", "वे": "वें"}
# The first six ordinals are lexical and written with their own endings: 1ला/1ली/1ले
# (पहला), 2रा (दूसरा), 3रा (तीसरा), 4था (चौथा), 6ठा (छठा); (digit, marker) -> spoken word.
LEXICAL_ORDINAL_WORDS = {
    ("1", "ला"): "पहला",
    ("1", "ली"): "पहली",
    ("1", "ले"): "पहले",
    ("2", "रा"): "दूसरा",
    ("2", "री"): "दूसरी",
    ("2", "रे"): "दूसरे",
    ("3", "रा"): "तीसरा",
    ("3", "री"): "तीसरी",
    ("3", "रे"): "तीसरे",
    ("4", "था"): "चौथा",
    ("4", "थी"): "चौथी",
    ("4", "थे"): "चौथे",
    ("6", "ठा"): "छठा",
    ("6", "ठी"): "छठी",
    ("6", "ठे"): "छठे",
}

# Devanagari block U+0900-U+097F; U+0966 DEVANAGARI DIGIT ZERO opens the digit run.
PROFILE = make_profile(
    LANG,
    zero="०",
    block=(0x0900, 0x0980),
    minus_word=MINUS_WORD,
    plus_word=PLUS_WORD,
    range_word=RANGE_WORD,
    point_word=POINT_WORD,
    point_words=POINT_WORDS,
    negative_words=("ऋण", "माइनस", "नेगेटिव", "मायनस"),
    case_suffixes=CASE_SUFFIXES,
)

HI_DIGIT = PROFILE.digits.digit
HI_LETTER = PROFILE.letter
ANUSVARA = "ं"  # U+0902 DEVANAGARI SIGN ANUSVARA
CHANDRABINDU = "ँ"  # U+0901 DEVANAGARI SIGN CANDRABINDU
NUKTA = "़"  # U+093C DEVANAGARI SIGN NUKTA

# Vulgar fraction signs read as their everyday words; with an integer they take the
# idiomatic forms डेढ़ (1½), ढाई (2½), साढ़े N, सवा N (N¼) and पौने N+1 (N¾).
VULGAR_WORDS = {"½": "आधा", "¼": "चौथाई", "¾": "पौन"}
# Conjunction between a whole number and a fraction (दो पूर्णांक तीन बटा चार).
AND_WORD = "पूर्णांक"
PART_NOUNS = ("भाग", "हिस्सा")
ITN_PART_NOUNS = ("भाग", "हिस्सा", "हिस्से")
BY_WORDS = ("बटा", "बटे", "बाय")
