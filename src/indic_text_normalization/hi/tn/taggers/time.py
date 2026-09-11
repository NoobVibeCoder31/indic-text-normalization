"""
The written Hindi clock vocabulary the shared time tagger reads.
"""

from indic_text_normalization.core.tn_taggers.time import TimeWords

# AM/PM travel as raw markers; the verbalizer picks the day-part word by the hour.
TIME_WORDS = TimeWords(
    hour_nouns=("बजे", "बजकर", "घंटे"),
    day_parts=("सुबह", "दोपहर", "शाम", "रात", "सवेरे", "प्रातः", "सायं"),
    day_part_abbreviations={},
    am="AM",
    pm="PM",
)
