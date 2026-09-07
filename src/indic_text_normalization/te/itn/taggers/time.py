"""
ITN tagger converting spoken Telugu times to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import load_labels
from indic_text_normalization.te.constants import DIGIT, TE_TO_ASCII_DIGIT, GraphFst, delete_space
from indic_text_normalization.te.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.te.utils import get_abs_path

# Suffixed hour/minute/second nouns and the written suffix they carry.
SUFFIXED_HOUR_WORDS = [
    ("గంటలకు", "కు"),
    ("గంటలకి", "కి"),
    ("గంటలకే", "కే"),
    ("గంటకు", "కు"),
    ("గంటకి", "కి"),
    ("గంటకే", "కే"),
    ("గంటలలో", "లో"),
    ("గంటలవరకు", "వరకు"),
]
SUFFIXED_MINUTE_WORDS = [
    ("నిమిషాలకు", "కు"),
    ("నిమిషాలకి", "కి"),
    ("నిమిషాలకే", "కే"),
    ("నిమిషానికి", "కి"),
    ("నిమిషానికే", "కే"),
    ("నిమిషాలలో", "లో"),
    ("నిమిషాలవరకు", "వరకు"),
]
SUFFIXED_SECOND_WORDS = [
    ("సెకన్లకు", "కు"),
    ("సెకన్లకి", "కి"),
    ("సెకనుకి", "కి"),
    ("సెకనుకు", "కు"),
]


def _table_words(name: str) -> pynini.Fst:
    """
    Spoken word -> ASCII digits for one time table (keys are Telugu digits).
    """
    rows = [r for r in load_labels(get_abs_path(f"data/time/{name}.tsv")) if len(r) >= 2]
    to_ascii = pynini.closure(pynini.union(TE_TO_ASCII_DIGIT, DIGIT))
    return (pynini.invert(pynini.string_map([(k, v) for k, v, *_ in rows])) @ to_ascii).optimize()


class TimeFst(GraphFst):
    """
    Finite state transducer for classifying spoken times, e.g.
        పది గంటల ముప్పై నిమిషాలు -> time { hours: "10" minutes: "30" }
        పది గంటలకు -> time { hours: "10" suffix: "కు" }
        ఒంటి గంట -> time { hours: "1" }
        పదిన్నర గంటలకు -> time { hours: "10" minutes: "30" suffix: "కు" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="time", kind="classify", deterministic=deterministic)

        # Any spoken number may head a time; the verbalizer reads an hour above 23 back as a
        # plain number so ఇరవై ఐదు గంటలకు is 25 గంటలకు rather than 20 5:00కు.
        hour_words = pynini.union(
            cardinal.words_to_digits,
            cardinal.pre_map @ (_table_words("hours") | pynini.cross("ఒకటి", "1")),
        ).optimize()
        minute_words = cardinal.pre_map @ (_table_words("minutes") | pynini.cross("ఒక", "01"))
        second_words = cardinal.pre_map @ (_table_words("seconds") | pynini.cross("ఒక", "01"))

        def suffixed(pairs: list[tuple[str, str]]) -> pynini.Fst:
            return pynutil.insert(' suffix: "') + pynini.string_map(pairs) + pynutil.insert('"')

        hour_plain = pynutil.delete(pynini.union("గంటల", "గంట", "గంటలు"))
        minute_plain = pynutil.delete(pynini.union("నిమిషాలు", "నిమిషాల", "నిమిషం", "నిమిషములు"))
        second_plain = pynutil.delete(
            pynini.union("సెకన్లు", "సెకన్ల", "సెకను", "సెకండ్లు", "సెకన్డ్లు")
        )

        hours = pynutil.insert('hours: "') + hour_words + pynutil.insert('"')
        minutes = pynutil.insert(' minutes: "') + minute_words + pynutil.insert('"')
        seconds = pynutil.insert(' seconds: "') + second_words + pynutil.insert('"')

        # Bare "X గంటలు" is a duration; the hour-only form converts only with a dative
        # (పది గంటలకు) or for the unambiguous clock reading ఒంటి గంట.
        graph_h = hours + delete_space + suffixed(SUFFIXED_HOUR_WORDS)
        graph_h |= (
            pynutil.insert('hours: "')
            + pynini.cross("ఒంటి", "1")
            + pynutil.insert('"')
            + delete_space
            + pynutil.delete("గంట")
        )
        graph_hm = (
            hours
            + delete_space
            + hour_plain
            + delete_space
            + minutes
            + delete_space
            + (minute_plain | suffixed(SUFFIXED_MINUTE_WORDS))
        )
        graph_hms = (
            hours
            + delete_space
            + hour_plain
            + delete_space
            + minutes
            + delete_space
            + minute_plain
            + delete_space
            + seconds
            + delete_space
            + (second_plain | suffixed(SUFFIXED_SECOND_WORDS))
        )
        graph_hs = (
            hours
            + delete_space
            + hour_plain
            + delete_space
            + seconds
            + delete_space
            + (second_plain | suffixed(SUFFIXED_SECOND_WORDS))
        )

        # Half-hour idiom: పదిన్నర గంటలకు -> 10:30.
        half_rows = [
            r
            for r in load_labels(get_abs_path("data/numbers/itn_half_forms.tsv"))
            if len(r) >= 3 and r[1] != "0"
        ]
        half_words = pynini.string_map([(w, ip) for w, ip, _ in half_rows])
        # Bare "Xన్నర గంటలు" is a duration (2.5 hours), so the clock reading needs a dative.
        glued_suffix = (
            pynutil.insert(' suffix: "') + pynini.union("కి", "కు", "కే") + pynutil.insert('"')
        )
        graph_half = (
            pynutil.insert('hours: "')
            + half_words
            + pynutil.insert('" minutes: "30"')
            + (delete_space + suffixed(SUFFIXED_HOUR_WORDS) | glued_suffix)
        )

        graph = (graph_hms | graph_hm | graph_hs | graph_h | graph_half) + pynutil.insert(
            " preserve_order: true"
        )
        self.fst = self.add_tokens(graph).optimize()
