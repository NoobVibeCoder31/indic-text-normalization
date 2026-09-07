"""
ITN tagger converting spoken Telugu decimals to digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import load_labels
from indic_text_normalization.te.constants import (
    DIGIT,
    POINT_WORD,
    GraphFst,
    delete_space,
    insert_space,
)
from indic_text_normalization.te.itn.taggers.cardinal import NEGATIVE_WORDS, CardinalFst
from indic_text_normalization.te.utils import get_abs_path

POINT_WORDS = [POINT_WORD, "పాయింట్", "పాయింటు", "పాయింట", "పాయిoట్", "డెసిమల్"]


class DecimalFst(GraphFst):
    """
    Finite state transducer for classifying spoken decimals, e.g.
        పన్నెండు దశాంశం ఐదు -> decimal { integer_part: "12" fractional_part: "5" }
        ఒకటిన్నర -> decimal { integer_part: "1" fractional_part: "5" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="classify", deterministic=deterministic)

        # Fractional digits are spoken one or two at a time; a scale word after the
        # fraction is a quantity, never more digits (ఐదు దశాంశం ఐదు లక్షలు -> 5.5 లక్షలు).
        short = cardinal.words_to_digits @ pynini.closure(DIGIT, 1, 3)
        digit_by_digit = short + pynini.closure(delete_space + short)
        self.fractional_digits = digit_by_digit
        point = pynutil.delete(pynini.union(*POINT_WORDS))

        integer_part = (
            pynutil.insert('integer_part: "') + cardinal.words_to_digits + pynutil.insert('"')
        )
        fractional_part = (
            pynutil.insert('fractional_part: "') + digit_by_digit + pynutil.insert('"')
        )

        negative = pynini.union(*[pynini.cross(w + " ", '"true" ') for w in NEGATIVE_WORDS])
        optional_minus = pynini.closure(pynutil.insert("negative: ") + negative, 0, 1)

        graph = (
            optional_minus
            + integer_part
            + delete_space
            + point
            + delete_space
            + insert_space
            + fractional_part
        )

        # Dotted chains round-trip: ఒకటి దశాంశం రెండు దశాంశం మూడు -> 1.2.3.
        chain_fraction = (
            pynutil.insert('fractional_part: "')
            + digit_by_digit
            + pynini.closure(pynini.cross(f" {POINT_WORD} ", ".") + digit_by_digit, 1)
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(
            optional_minus
            + integer_part
            + delete_space
            + point
            + delete_space
            + insert_space
            + chain_fraction,
            -0.1,
        )

        # Fused fractional words: ఒకటిన్నర -> 1.5, పావు -> 0.25, ముప్పావు -> 0.75.
        half_forms = pynini.union(
            *[
                pynini.cross(word, f'integer_part: "{ip}" fractional_part: "{fp}"')
                for word, ip, fp in load_labels(get_abs_path("data/numbers/itn_half_forms.tsv"))
            ]
        )
        graph |= half_forms

        self.fst = self.add_tokens(graph).optimize()
