"""
Hindi TN decimal verbalizer.
"""

import pynini

from indic_text_normalization.core.graph_utils import SIGMA
from indic_text_normalization.core.tn_verbalizers import QuantityDecimalFst
from indic_text_normalization.hi.constants import MINUS_WORD, POINT_WORD


class DecimalFst(QuantityDecimalFst):
    """
    Decimals; a whole number before a scale word is spoken as tagged (पाँच लाख, एक करोड़):
        decimal { integer_part: "बारह" fractional_part: "पाँच" } -> बारह दशमलव पाँच
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            minus_word=MINUS_WORD,
            point_word=POINT_WORD,
            whole_quantity=pynini.cdrewrite(pynini.accep(""), "", "", SIGMA),
            deterministic=deterministic,
        )
