"""
The written Malayalam clock vocabulary the shared time tagger reads.
"""

from indic_text_normalization.core.tn_taggers.time import TimeWords

# AM/PM travel as raw markers; the verbalizer picks the day-part word by the hour.
TIME_WORDS = TimeWords(
    hour_nouns=("മണി", "മ."),
    hour_noun_suffixes=(("മണിക്ക്", "ന്"), ("മണിയോടെ", "ഓടെ"), ("മണിയായി", "ആയി")),
    day_parts=("രാവിലെ", "ഉച്ചയ്ക്ക്", "ഉച്ചക്ക്", "വൈകുന്നേരം", "വൈകിട്ട്", "രാത്രി", "പുലർച്ചെ"),
    day_part_abbreviations={},
    am="AM",
    pm="PM",
)
