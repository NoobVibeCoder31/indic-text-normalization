"""
ITN tagger converting spoken digit sequences to telephone numbers.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst, delete_space
from indic_text_normalization.ta.utils import get_abs_path

digit_words = pynini.invert(
    pynini.string_file(get_abs_path("data/telephone/number.tsv"))
).optimize()


class TelephoneFst(GraphFst):
    """
    Finite state transducer for classifying spoken telephone numbers, e.g. a
    sequence of ten digit words -> telephone { number_part: "9943206870" }
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="classify", deterministic=deterministic)

        # பூஜ்ஜியம் is a common variant of பூஜ்யம்.
        digit = pynini.union(digit_words, pynini.cross("பூஜ்ஜியம்", "0")).optimize()

        # Ten digit words in a row (Indian mobile length).
        number = digit + pynini.closure(delete_space + digit, 9, 9)

        country_code = (
            pynutil.insert('country_code: "')
            + pynini.cross("பிளஸ்", "+")
            + pynini.closure(delete_space + digit, 1, 3)
            + pynutil.insert('" ')
            + delete_space
        )

        graph = (
            pynini.closure(country_code, 0, 1)
            + pynutil.insert('number_part: "')
            + number
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()
