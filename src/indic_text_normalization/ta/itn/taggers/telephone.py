"""
ITN tagger converting spoken digit sequences to telephone numbers.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import delete_space, GraphFst
from indic_text_normalization.ta.constants import LANG

digit_words = pynini.invert(pynini.string_file(data_path(LANG, "telephone/number.tsv"))).optimize()


class TelephoneFst(GraphFst):
    """
    Finite state transducer for classifying spoken telephone numbers, e.g. a
    sequence of ten digit words -> telephone { number_part: "9943206870" }
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="classify", deterministic=deterministic)

        # பூஜ்ஜியம் is a common variant of பூஜ்யம்.
        digit = pynini.union(digit_words, pynini.cross("பூஜ்ஜியம்", "0")).optimize()

        # Ten to twelve digit words in a row: mobiles, landlines with an STD code
        # (044-28230000) and toll-free numbers (1800-425-1234).
        number = digit + pynini.closure(delete_space + digit, 9, 11)

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
