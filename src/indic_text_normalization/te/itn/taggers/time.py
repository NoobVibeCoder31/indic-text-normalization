"""
The spoken Telugu clock vocabulary the shared ITN time tagger reads.
"""

from indic_text_normalization.core.itn_taggers.time import ItnTimeWords

ITN_TIME_WORDS = ItnTimeWords(
    hour_nouns=("గంటల", "గంట", "గంటలు"),
    minute_nouns=("నిమిషాలు", "నిమిషాల", "నిమిషం", "నిమిషములు"),
    second_nouns=("సెకన్లు", "సెకన్ల", "సెకను", "సెకండ్లు", "సెకన్డ్లు"),
    hour_suffixed=(
        ("గంటలకు", "కు"),
        ("గంటలకి", "కి"),
        ("గంటలకే", "కే"),
        ("గంటకు", "కు"),
        ("గంటకి", "కి"),
        ("గంటకే", "కే"),
        ("గంటలలో", "లో"),
        ("గంటలవరకు", "వరకు"),
    ),
    minute_suffixed=(
        ("నిమిషాలకు", "కు"),
        ("నిమిషాలకి", "కి"),
        ("నిమిషాలకే", "కే"),
        ("నిమిషానికి", "కి"),
        ("నిమిషానికే", "కే"),
        ("నిమిషాలలో", "లో"),
        ("నిమిషాలవరకు", "వరకు"),
    ),
    second_suffixed=(
        ("సెకన్లకు", "కు"),
        ("సెకన్లకి", "కి"),
        ("సెకనుకి", "కి"),
        ("సెకనుకు", "కు"),
    ),
    hour_one=("ఒంటి", "గంట"),
    minute_one="ఒక",
    half_glued_suffixes=(("కి", "కి"), ("కు", "కు"), ("కే", "కే")),
)
