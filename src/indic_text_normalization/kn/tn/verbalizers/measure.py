"""
Kannada TN measure verbalizer.
"""

from indic_text_normalization.core.tn_verbalizers import InvariantMeasureFst
from indic_text_normalization.kn.constants import MINUS_WORD
from indic_text_normalization.kn.morphology import ANY_WORD, optional_suffix_field, suffix_sandhi


class MeasureFst(InvariantMeasureFst):
    """
    Measures with invariant unit nouns:
        measure { amount: "ಐದು" units: "ಕಿಲೋಗ್ರಾಂ" suffix: "ಕ್ಕೆ" } -> ಐದು ಕಿಲೋಗ್ರಾಂಗೆ
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            minus_word=MINUS_WORD,
            amount=ANY_WORD,
            suffix_field=optional_suffix_field(),
            sandhi=suffix_sandhi(),
            deterministic=deterministic,
        )
