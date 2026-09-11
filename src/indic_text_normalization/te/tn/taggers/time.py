"""
The written Telugu clock vocabulary the shared time tagger reads.
"""

from indic_text_normalization.core.tn_taggers.time import TimeWords

TIME_WORDS = TimeWords(
    hour_nouns=("గంటలు", "గంటల", "గంట", "గం.", "గం"),
    hour_noun_suffixes=(
        ("గంటలకు", "కు"),
        ("గంటలకి", "కి"),
        ("గంటలకే", "కే"),
        ("గంటలలో", "లో"),
        ("గంటలలోపు", "లోపు"),
        ("గంటలవరకు", "వరకు"),
        ("గంటల వరకు", "వరకు"),
        ("గంటకు", "కు"),
        ("గంటకి", "కి"),
    ),
    extra_suffixes=("లోపు",),
    day_parts=(
        "ఉదయం",
        "ఉదయాన్నే",
        "తెల్లవారుజామున",
        "మధ్యాహ్నం",
        "సాయంత్రం",
        "రాత్రి",
        "పూర్వాహ్నం",
        "అపరాహ్నం",
    ),
    day_part_abbreviations={"ఉ.": "ఉదయం", "సా.": "సాయంత్రం", "మ.": "మధ్యాహ్నం", "రా.": "రాత్రి"},
    am="పూర్వాహ్నం",
    pm="అపరాహ్నం",
)
