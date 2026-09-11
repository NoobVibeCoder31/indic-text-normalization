"""
Kannada TN money verbalizer.
"""

from indic_text_normalization.core.tn_verbalizers import InvariantMoneyFst
from indic_text_normalization.kn.constants import LANG, MINUS_WORD
from indic_text_normalization.kn.morphology import ANY_WORD, optional_suffix_field, suffix_sandhi


class MoneyFst(InvariantMoneyFst):
    """
    Money with invariant currency nouns:
        money { integer_part: "ಐವತ್ತು" currency_maj: "ರೂಪಾಯಿ" suffix: "ಕ್ಕೆ" } -> ಐವತ್ತು ರೂಪಾಯಿಗೆ
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            lang=LANG,
            minus_word=MINUS_WORD,
            amount=ANY_WORD,
            zero_word="ಸೊನ್ನೆ",
            suffix_field=optional_suffix_field(),
            sandhi=suffix_sandhi(),
            deterministic=deterministic,
        )
