"""
ITN tagger converting spoken Telugu money amounts to symbol-and-digit form.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import (
    CASE_SUFFIXES,
    DIGIT,
    GraphFst,
    delete_space,
)
from indic_text_normalization.te.itn.taggers.cardinal import NEGATIVE_WORDS, CardinalFst
from indic_text_normalization.te.itn.taggers.decimal import POINT_WORDS
from indic_text_normalization.te.utils import get_abs_path

MINOR_WORDS = [
    "పైసా",
    "పైసలు",
    "పైసల",
    "పైసలకి",
    "సెంట్",
    "సెంట్లు",
    "సెంట్ల",
    "పెన్నీ",
    "పెన్నీలు",
    "పెన్స్",
    "సెన్",
    "సెన్లు",
]


class MoneyFst(GraphFst):
    """
    Finite state transducer for classifying spoken money, e.g.
        యాభై రూపాయలు -> money { currency: "₹" integer_part: "50" }
        యాభై రూపాయల యాభై పైసలు -> money { currency: "₹" integer_part: "50" fractional_part: "50" }
        ఒక రూపాయి -> money { currency: "₹" integer_part: "1" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="money", kind="classify", deterministic=deterministic)

        currency = pynini.string_file(get_abs_path("data/money/currency_itn.tsv"))
        # A case suffix on the currency word is carried into the written form (₹50కి).
        optional_suffix = pynini.closure(
            pynutil.insert(' suffix: "') + pynini.union(*CASE_SUFFIXES) + pynutil.insert('"'), 0, 1
        )
        currency_field = (
            pynutil.insert(' currency: "') + currency + pynutil.insert('"') + optional_suffix
        )
        minor_unit = pynutil.delete(pynini.union(*MINOR_WORDS))

        amount_words = pynini.union(cardinal.words_to_digits, pynini.cross("ఒక", "1"))
        range_words = (
            cardinal.words_to_digits
            + pynini.cross(pynini.union(" నుండి ", " నుంచి "), "-")
            + cardinal.words_to_digits
        )
        integer_part = (
            pynutil.insert('integer_part: "')
            + (amount_words | pynutil.add_weight(range_words, -0.5))
            + pynutil.insert('"')
        )
        # A lone fractional digit is a tens value in paise (ఐదు పైసలు -> .05).
        two_digits = pynini.union(DIGIT + DIGIT, pynutil.insert("0") + DIGIT)
        fractional_part = (
            pynutil.insert(' fractional_part: "')
            + (amount_words @ two_digits)
            + pynutil.insert('"')
        )

        graph = (
            integer_part
            + delete_space
            + currency_field
            + pynini.closure(delete_space + fractional_part + delete_space + minor_unit, 0, 1)
        )

        # Currency word first: రూపాయలు యాభై -> ₹50.
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

        # Quantity-word money keeps the written idiom: ఐదు కోట్ల రూపాయలు -> ₹5 కోట్లు,
        # రెండు దశాంశం ఐదు లక్షల రూపాయలు -> ₹2.5 లక్షలు. Thousands are spelled out.
        quantity_written = pynini.union(
            pynini.accep("కోటి"),
            pynini.accep("కోట్లు"),
            pynini.cross("కోట్ల", "కోట్లు"),
            pynini.accep("లక్ష"),
            pynini.accep("లక్షలు"),
            pynini.cross("లక్షల", "లక్షలు"),
            pynini.accep("మిలియన్"),
            pynini.accep("బిలియన్"),
        )
        short = cardinal.words_to_digits @ pynini.closure(DIGIT, 1, 2)
        frac_digits = short + pynini.closure(delete_space + short)
        point = pynini.cross(pynini.accep(" ") + pynini.union(*POINT_WORDS) + " ", ".")
        amount_digits = amount_words + pynini.closure(point + frac_digits, 0, 1)
        quantity_amount = (
            pynutil.insert('integer_part: "')
            + amount_digits
            + pynini.accep(" ")
            + quantity_written
            + pynutil.insert('"')
        )
        # A bare scale word counts one: లక్ష రూపాయలు -> ₹1 లక్ష.
        quantity_amount |= (
            pynutil.insert('integer_part: "1 ')
            + pynini.union("లక్ష", "కోటి", "మిలియన్", "బిలియన్")
            + pynutil.insert('"')
        )
        graph_quantity = quantity_amount + delete_space + currency_field
        graph |= pynutil.add_weight(graph_quantity, -1.0)

        # Spoken negative folds into the amount: ఋణ ఐదు వందల రూపాయలు -> -₹500.
        negative = pynini.union(*[pynini.cross(w + " ", '"true" ') for w in NEGATIVE_WORDS])
        graph_negative = (
            pynutil.insert("negative: ") + negative + integer_part + delete_space + currency_field
        )
        graph |= graph_negative

        # Paise-only amounts: యాభై పైసలు -> ₹0.50.
        paise_only = (
            pynutil.insert('currency: "₹" integer_part: "0"')
            + fractional_part
            + delete_space
            + pynutil.delete(pynini.union("పైసా", "పైసలు", "పైసల"))
        )
        graph |= paise_only

        self.fst = self.add_tokens(graph).optimize()
