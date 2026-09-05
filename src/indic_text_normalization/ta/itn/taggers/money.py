"""
ITN tagger converting spoken Tamil money amounts to symbol-and-digit form.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst, delete_space
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.utils import get_abs_path


class MoneyFst(GraphFst):
    """
    Finite state transducer for classifying spoken money, e.g.
        ஐம்பது ரூபாய் -> money { currency: "₹" integer_part: "50" }
        ஐம்பது ரூபாய் ஐம்பது பைசா -> money { currency: "₹" integer_part: "50" fractional_part: "50" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="money", kind="classify", deterministic=deterministic)

        currency = pynini.string_file(get_abs_path("data/money/currency_itn.tsv"))
        minor_unit = pynutil.delete(pynini.union("பைசா", "காசு", "சென்ட்"))

        integer_part = (
            pynutil.insert('integer_part: "') + cardinal.words_to_digits + pynutil.insert('"')
        )
        fractional_part = (
            pynutil.insert(' fractional_part: "') + cardinal.words_to_digits + pynutil.insert('"')
        )

        graph = (
            integer_part
            + delete_space
            + pynutil.insert(' currency: "')
            + currency
            + pynutil.insert('"')
            + pynini.closure(delete_space + fractional_part + delete_space + minor_unit, 0, 1)
        )
        self.fst = self.add_tokens(graph).optimize()
