"""
ITN tagger converting spoken Tamil times to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst, delete_space
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class TimeFst(GraphFst):
    """
    Finite state transducer for classifying spoken times, e.g.
        பத்து மணி முப்பது நிமிடம் -> time { hours: "10" minutes: "30" }
        பத்து மணி -> time { hours: "10" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="time", kind="classify", deterministic=deterministic)

        mani = pynutil.delete(pynini.union("மணிக்கு", "மணி"))
        minute_word = pynutil.delete(pynini.union("நிமிடங்கள்", "நிமிடம்", "நிமிடத்திற்கு"))
        second_word = pynutil.delete(pynini.union("வினாடிகள்", "வினாடி", "நொடி"))

        hours = pynutil.insert('hours: "') + cardinal.words_to_digits + pynutil.insert('"')
        minutes = pynutil.insert(' minutes: "') + cardinal.words_to_digits + pynutil.insert('"')
        seconds = pynutil.insert(' seconds: "') + cardinal.words_to_digits + pynutil.insert('"')

        graph_h = hours + delete_space + mani
        graph_hm = graph_h + delete_space + minutes + delete_space + minute_word
        graph_hms = graph_hm + delete_space + seconds + delete_space + second_word

        graph = (graph_hms | graph_hm | graph_h) + pynutil.insert(" preserve_order: true")
        self.fst = self.add_tokens(graph).optimize()
