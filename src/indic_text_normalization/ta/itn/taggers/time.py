"""
ITN tagger converting spoken Tamil times to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    CLOCK_MAX_HOUR,
    CLOCK_MAX_MINUTE,
    GraphFst,
    delete_space,
)
from indic_text_normalization.ta.itn.fused import (
    FRACTION_MINUTES,
    half_form_rows,
    quarter_form_graph,
)
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst

# Day-part words the TN grammar emits before a clock hour (காலை பத்து மணி).
DAY_PARTS = ["காலை", "அதிகாலை", "மதியம்", "நண்பகல்", "மாலை", "இரவு", "முற்பகல்", "பிற்பகல்"]


class TimeFst(GraphFst):
    """
    Finite state transducer for classifying spoken times, e.g.
        பத்து மணி முப்பது நிமிடம் -> time { hours: "10" minutes: "30" }
        பத்தரை மணிக்கு -> time { hours: "10" minutes: "30" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="time", kind="classify", deterministic=deterministic)

        mani = pynutil.delete(pynini.union("மணிக்கு", "மணி"))
        minute_word = pynutil.delete(
            pynini.union("நிமிடங்கள்", "நிமிடம்", "நிமிடத்திற்கு", "நிமிடத்தில்", "நிமிடத்துக்கு")
        )
        second_word = pynutil.delete(
            pynini.union("வினாடிகள்", "வினாடி", "வினாடிக்கு", "வினாடியில்", "நொடி")
        )

        # 24:00 and 10:60 are not clock readings, so the fields are range-bound here.
        number = cardinal.words_to_digits_with_article
        hour_value = number @ pynini.union(*[str(h) for h in range(CLOCK_MAX_HOUR + 1)])
        minute_value = number @ pynini.union(*[str(m) for m in range(CLOCK_MAX_MINUTE + 1)])

        hours = pynutil.insert('hours: "') + hour_value + pynutil.insert('"')
        minutes = pynutil.insert(' minutes: "') + minute_value + pynutil.insert('"')
        seconds = pynutil.insert(' seconds: "') + minute_value + pynutil.insert('"')

        # Bare "X மணி" is a duration (two hours), not a clock time; the hour-only
        # form converts only for the unambiguous "X மணிக்கு".
        graph_hm = hours + delete_space + mani + delete_space + minutes + delete_space + minute_word
        graph_hms = graph_hm + delete_space + seconds + delete_space + second_word
        # ASR drops மணி between the two numbers: பத்து முப்பது மணிக்கு -> 10:30.
        graph_hm_bare = hours + delete_space + minutes + delete_space + pynutil.delete("மணிக்கு")

        # Fused fractional hours: பத்தரை மணிக்கு -> 10:30, பத்தே கால் மணிக்கு -> 10:15. The bare
        # quarter words are durations (அரை மணி is half an hour), so they are excluded.
        fused_clock = pynini.union(
            *[
                pynini.cross(word, f'hours: "{ip}" minutes: "{FRACTION_MINUTES[fp]}"')
                for word, ip, fp in half_form_rows()
                if 0 < int(ip) < 24
            ]
        )
        fused_clock |= quarter_form_graph(
            hour_value,
            prefix='hours: "',
            infix='"',
            suffix=lambda fraction: f' minutes: "{FRACTION_MINUTES[fraction]}"',
        )

        # An hour on its own, spelled plainly or fused, needs the unambiguous மணிக்கு.
        hour_only = hours | fused_clock
        graph_h = hour_only + delete_space + pynutil.delete("மணிக்கு")

        graph = graph_hms | graph_hm | graph_h | graph_hm_bare

        # A day-part word before the hour makes even a bare "X மணி" a clock time.
        day_part = (
            pynutil.insert('day_part: "')
            + pynini.union(*DAY_PARTS)
            + pynutil.insert('" ')
            + pynutil.delete(" ")
        )
        # A day part is optional before any clock shape, and additionally licenses the
        # bare "X மணி" hour that is otherwise a duration.
        graph = pynini.closure(day_part, 0, 1) + graph | day_part + (
            hour_only + delete_space + pynutil.delete("மணி")
        )
        graph = graph + pynutil.insert(" preserve_order: true")
        self.fst = self.add_tokens(graph).optimize()
