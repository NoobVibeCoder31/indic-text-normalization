"""
Malayalam TN measure verbalizer.
"""

import pynini

from indic_text_normalization.core.tn_verbalizers import InvariantMeasureFst
from indic_text_normalization.ml.constants import MINUS_WORD
from indic_text_normalization.ml.morphology import (
    NOT_ONE,
    ONE_AS_ORU,
    optional_suffix_field,
    suffix_sandhi,
)


class MeasureFst(InvariantMeasureFst):
    """
    Measures with invariant unit nouns and the counting ഒരു:
        measure { amount: "അഞ്ച്" units: "കിലോഗ്രാം" suffix: "ൽ" } -> അഞ്ച് കിലോഗ്രാമിൽ
        measure { amount: "ഒന്ന്" units: "കിലോഗ്രാം" } -> ഒരു കിലോഗ്രാം
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            minus_word=MINUS_WORD,
            amount=pynini.union(ONE_AS_ORU, NOT_ONE),
            suffix_field=optional_suffix_field(),
            sandhi=suffix_sandhi(),
            deterministic=deterministic,
        )
