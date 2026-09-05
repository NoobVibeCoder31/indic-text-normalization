"""
ITN tagger converting spoken Tamil decimals to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import GraphFst, delete_space, insert_space
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.utils import get_abs_path
from indic_text_normalization.core.utils import load_labels


class DecimalFst(GraphFst):
    """
    Finite state transducer for classifying spoken decimals, e.g.
        பன்னிரண்டு புள்ளி ஐந்து -> decimal { integer_part: "12" fractional_part: "5" }
        ஒன்றரை -> decimal { integer_part: "1" fractional_part: "5" }
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

        # Dotted chains round-trip: ஒன்று புள்ளி இரண்டு புள்ளி மூன்று -> 1.2.3.
        chain_fraction = (
            pynutil.insert('fractional_part: "')
            + digit_by_digit
            + pynini.closure(pynini.cross(" புள்ளி ", ".") + digit_by_digit, 1)
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(
            optional_minus
            + integer_part
            + delete_space
            + pynutil.delete("புள்ளி")
            + delete_space
            + insert_space
            + chain_fraction,
            -0.1,
        )

        # Fused fractional words: ஒன்றரை -> 1.5, கால் -> 0.25, முக்கால் -> 0.75.
        half_forms = pynini.union(
            *[
                pynini.cross(word, f'integer_part: "{ip}" fractional_part: "{fp}"')
                for word, ip, fp in load_labels(get_abs_path("data/numbers/itn_half_forms.tsv"))
            ]
        )
        graph |= half_forms

        self.fst = self.add_tokens(graph).optimize()
