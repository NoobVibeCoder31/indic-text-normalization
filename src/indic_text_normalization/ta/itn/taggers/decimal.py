"""
ITN tagger converting spoken Tamil decimals to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import delete_space, DIGIT, GraphFst, insert_space
from indic_text_normalization.ta.constants import LANG, MINUS_WORD, PLUS_WORD
from indic_text_normalization.ta.itn.fused import half_form_rows, quarter_form_graph
from indic_text_normalization.core.scales import kept_scale_words
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class DecimalFst(GraphFst):
    """
    Finite state transducer for classifying spoken decimals, e.g.
        பன்னிரண்டு புள்ளி ஐந்து -> decimal { integer_part: "12" fractional_part: "5" }
        ஒன்றரை -> decimal { integer_part: "1" fractional_part: "5" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="classify", deterministic=deterministic)

        # A fractional piece is a single small number or a digit; bounding it to three
        # digits keeps a following scale word out of the fraction (ஐந்து புள்ளி ஐந்து லட்சம்
        # must not read as 5.500000).
        small = (cardinal.words_to_digits @ pynini.closure(DIGIT, 1, 3)).optimize()
        digit_by_digit = small + pynini.closure(delete_space + small)

        integer_part = (
            pynutil.insert('integer_part: "') + cardinal.words_to_digits + pynutil.insert('"')
        )
        # Dotted chains round-trip too: ஒன்று புள்ளி இரண்டு புள்ளி மூன்று -> 1.2.3.
        fractional_part = (
            pynutil.insert('fractional_part: "')
            + digit_by_digit
            + pynini.closure(pynini.cross(" புள்ளி ", ".") + digit_by_digit)
            + pynutil.insert('"')
        )

        optional_sign = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross(f"{MINUS_WORD} ", '"true" ')
            | pynutil.insert("positive: ") + pynini.cross(f"{PLUS_WORD} ", '"true" '),
            0,
            1,
        )
        delete_point = delete_space + pynutil.delete("புள்ளி") + delete_space

        graph = optional_sign + integer_part + delete_point + insert_space + fractional_part

        # A trailing scale word keeps the written idiom (ஐந்து புள்ளி ஐந்து லட்சம் -> 5.5 லட்சம்)
        # instead of being multiplied into the fractional digits.
        short_fraction = pynutil.insert('fractional_part: "') + small + pynutil.insert('"')
        quantity = (
            pynutil.insert(' quantity: "')
            + pynutil.delete(" ")
            + pynini.union(*kept_scale_words(LANG))
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(
            optional_sign + integer_part + delete_point + insert_space + short_fraction + quantity,
            -0.2,
        )

        # Fused fractional words: ஒன்றரை -> 1.5, கால் -> 0.25, முக்கால் -> 0.75.
        half_forms = pynini.union(
            *[
                pynini.cross(word, f'integer_part: "{ip}" fractional_part: "{fp}"')
                for word, ip, fp in half_form_rows()
            ]
        )
        # ே-linked quarter phrases: பத்தே கால் -> 10.25, ஒன்றேமுக்கால் -> 1.75. The stem is
        # bounded, so `small` is composed rather than the whole number grammar.
        quarter_forms = quarter_form_graph(
            small,
            prefix='integer_part: "',
            infix='"',
            suffix=lambda fraction: f' fractional_part: "{fraction}"',
        )
        graph |= half_forms | quarter_forms

        self.fst = self.add_tokens(graph).optimize()
