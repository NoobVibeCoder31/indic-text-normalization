"""
ITN tagger converting spoken Tamil decimals to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst, delete_space, insert_space
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class DecimalFst(GraphFst):
    """
    Finite state transducer for classifying spoken decimals, e.g.
        பன்னிரண்டு புள்ளி ஐந்து -> decimal { integer_part: "12" fractional_part: "5" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="classify", deterministic=deterministic)

        digit_by_digit = cardinal.words_to_digits + pynini.closure(
            delete_space + cardinal.words_to_digits
        )

        integer_part = (
            pynutil.insert('integer_part: "') + cardinal.words_to_digits + pynutil.insert('"')
        )
        fractional_part = (
            pynutil.insert('fractional_part: "') + digit_by_digit + pynutil.insert('"')
        )

        optional_minus = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("மைனஸ் ", '"true" '), 0, 1
        )

        graph = (
            optional_minus
            + integer_part
            + delete_space
            + pynutil.delete("புள்ளி")
            + delete_space
            + insert_space
            + fractional_part
        )
        self.fst = self.add_tokens(graph).optimize()
