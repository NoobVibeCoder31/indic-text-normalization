"""
The spoken Kannada clock vocabulary the shared ITN time tagger reads.
"""

from indic_text_normalization.core.itn_taggers.time import ItnTimeWords

ITN_TIME_WORDS = ItnTimeWords(
    hour_nouns=("ಗಂಟೆ", "ಗಂಟೆಗಳು"),
    minute_nouns=("ನಿಮಿಷ", "ನಿಮಿಷಗಳು"),
    second_nouns=("ಸೆಕೆಂಡ್", "ಸೆಕೆಂಡು", "ಸೆಕೆಂಡುಗಳು", "ಸೆಕೆಂಡ್ಗಳು"),
    hour_suffixed=(
        ("ಗಂಟೆಗೆ", "ಕ್ಕೆ"),
        ("ಗಂಟೆಯೊಳಗೆ", "ರೊಳಗೆ"),
        ("ಗಂಟೆಯಲ್ಲಿ", "ರಲ್ಲಿ"),
        ("ಗಂಟೆಯವರೆಗೆ", "ರವರೆಗೆ"),
    ),
    minute_suffixed=(("ನಿಮಿಷಕ್ಕೆ", "ಕ್ಕೆ"), ("ನಿಮಿಷದೊಳಗೆ", "ರೊಳಗೆ"), ("ನಿಮಿಷದಲ್ಲಿ", "ರಲ್ಲಿ")),
    second_suffixed=(("ಸೆಕೆಂಡ್ಗೆ", "ಕ್ಕೆ"), ("ಸೆಕೆಂಡಿಗೆ", "ಕ್ಕೆ")),
    half_glued_suffixes=(("ಗೆ", "ಕ್ಕೆ"),),
)
