"""
Kannada TN decimal verbalizer.
"""

import pynini

from indic_text_normalization.core.graph_utils import SIGMA
from indic_text_normalization.core.tn_verbalizers import QuantityDecimalFst
from indic_text_normalization.kn.constants import MINUS_WORD, POINT_WORD


class DecimalFst(QuantityDecimalFst):
    """
    Decimals; a whole number before a scale word is spoken as tagged (ಐದು ಲಕ್ಷ, ಒಂದು ಕೋಟಿ):
        decimal { integer_part: "ಹನ್ನೆರಡು" fractional_part: "ಐದು" } -> ಹನ್ನೆರಡು ದಶಾಂಶ ಐದು
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            minus_word=MINUS_WORD,
            point_word=POINT_WORD,
            whole_quantity=pynini.cdrewrite(pynini.accep(""), "", "", SIGMA),
            deterministic=deterministic,
        )
