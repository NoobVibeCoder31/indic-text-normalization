"""
Malayalam TN decimal verbalizer.
"""

from indic_text_normalization.core.tn_verbalizers import QuantityDecimalFst
from indic_text_normalization.ml.constants import MINUS_WORD, POINT_WORD
from indic_text_normalization.ml.morphology import fuse_thousand, one_before_scale


class DecimalFst(QuantityDecimalFst):
    """
    Decimals with the counting ഒരു before a scale word and a fused thousand:
        decimal { integer_part: "ഒന്ന്" quantity: "ലക്ഷം" } -> ഒരു ലക്ഷം
        decimal { integer_part: "അഞ്ച്" quantity: "ആയിരം" } -> അഞ്ചായിരം
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            minus_word=MINUS_WORD,
            point_word=POINT_WORD,
            whole_quantity=(one_before_scale() @ fuse_thousand()).optimize(),
            deterministic=deterministic,
        )
