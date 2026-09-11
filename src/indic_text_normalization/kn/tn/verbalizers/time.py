"""
Kannada TN time verbalizer.
"""

from indic_text_normalization.core.tn_verbalizers import InvariantTimeFst
from indic_text_normalization.kn.constants import LANG
from indic_text_normalization.kn.morphology import ANY_WORD, optional_suffix_field, suffix_sandhi


class TimeFst(InvariantTimeFst):
    """
    Clock times with invariant nouns and the day part by hour:
        time { hours: "ಹತ್ತು" minutes: "ಮೂವತ್ತು" } -> ಹತ್ತು ಗಂಟೆ ಮೂವತ್ತು ನಿಮಿಷ
        time { hours: "ಹತ್ತು" suffix: "ಕ್ಕೆ" } -> ಹತ್ತು ಗಂಟೆಗೆ
        time { hours: "ಹತ್ತು" meridiem: "PM" } -> ರಾತ್ರಿ ಹತ್ತು ಗಂಟೆ
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            lang=LANG,
            nouns=("ಗಂಟೆ", "ನಿಮಿಷ", "ಸೆಕೆಂಡ್"),
            count=ANY_WORD,
            suffix_field=optional_suffix_field(),
            sandhi=suffix_sandhi(),
            deterministic=deterministic,
        )
