"""
The spoken Hindi clock vocabulary the shared ITN time tagger reads.
"""

from indic_text_normalization.core.itn_taggers.time import ItnTimeWords

ITN_TIME_WORDS = ItnTimeWords(
    hour_nouns=("बजकर",),
    minute_nouns=("मिनट", "मिनिट"),
    second_nouns=("सेकंड", "सेकेंड", "सेकण्ड", "सेकंड्स"),
    # दस बजे is always ten o'clock, never a duration.
    clock_hour_nouns=("बजे",),
)
