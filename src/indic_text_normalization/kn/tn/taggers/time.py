"""
The written Kannada clock vocabulary the shared time tagger reads.
"""

from indic_text_normalization.core.tn_taggers.time import TimeWords

# AM/PM travel as raw markers; the verbalizer picks the day-part word by the hour.
TIME_WORDS = TimeWords(
    hour_nouns=("ಗಂಟೆ", "ಗಂಟೆಗಳು", "ಗಂ.", "ಗಂ"),
    hour_noun_suffixes=(
        ("ಗಂಟೆಗೆ", "ಕ್ಕೆ"),
        ("ಗಂಟೆಯೊಳಗೆ", "ರೊಳಗೆ"),
        ("ಗಂಟೆಯಲ್ಲಿ", "ರಲ್ಲಿ"),
        ("ಗಂಟೆಯವರೆಗೆ", "ರವರೆಗೆ"),
    ),
    day_parts=("ಬೆಳಿಗ್ಗೆ", "ಬೆಳಗ್ಗೆ", "ಮುಂಜಾನೆ", "ಮಧ್ಯಾಹ್ನ", "ಸಂಜೆ", "ರಾತ್ರಿ"),
    day_part_abbreviations={},
    am="AM",
    pm="PM",
)
