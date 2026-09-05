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

        # Currency word first: ரூபாய் ஐம்பது -> ₹50.
        currency_first = (
            pynutil.insert('currency: "')
            + currency
            + pynutil.insert('"')
            + delete_space
            + pynutil.insert(" ")
            + integer_part
            + pynutil.insert(" preserve_order: true")
        )
        graph |= currency_first

        # Quantity-word money keeps the written idiom: ஐந்து கோடி ரூபாய் -> ₹5 கோடி,
        # இரண்டு புள்ளி ஐந்து லட்சம் ரூபாய் -> ₹2.5 லட்சம்.
        quantity_written = pynini.union(
            "கோடி", "இலட்சம்", "லட்சம்", "ஆயிரம்", "மில்லியன்", "பில்லியன்"
        )
        frac_digits = cardinal.words_to_digits + pynini.closure(
            delete_space + cardinal.words_to_digits
        )
        amount_digits = cardinal.words_to_digits + pynini.closure(
            pynini.cross(" புள்ளி ", ".") + frac_digits, 0, 1
        )
        quantity_amount = (
            pynutil.insert('integer_part: "')
            + amount_digits
            + pynini.accep(" ")
            + quantity_written
            + pynutil.insert('"')
        )
        graph_quantity = (
            quantity_amount
            + delete_space
            + pynutil.insert(' currency: "')
            + currency
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(graph_quantity, -1.0)

        # Spoken minus folds into the amount: மைனஸ் ஐந்நூறு ரூபாய் -> -₹500.
        graph_negative = (
            pynutil.insert("negative: ")
            + pynini.cross("மைனஸ் ", '"true" ')
            + integer_part
            + delete_space
            + pynutil.insert(' currency: "')
            + currency
            + pynutil.insert('"')
        )
        graph |= graph_negative

        # Paise-only amounts: ஐம்பது பைசா -> ₹0.50.
        paise_only = (
            pynutil.insert('currency: "₹" integer_part: "0"')
            + fractional_part
            + delete_space
            + pynutil.delete(pynini.union("பைசா", "காசு"))
        )
        graph |= paise_only

        self.fst = self.add_tokens(graph).optimize()
