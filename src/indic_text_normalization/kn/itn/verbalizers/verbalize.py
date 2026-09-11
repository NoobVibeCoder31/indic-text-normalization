"""
Union of all Kannada ITN per-class verbalizers.
"""

from indic_text_normalization.core import itn_verbalizers as generic
from indic_text_normalization.core.graph_utils import GraphFst

DURATION_NOUNS = ("ಗಂಟೆ", "ನಿಮಿಷ")
# A written suffix glued to the hour noun and to the minute noun of a duration.
DURATION_SUFFIXES = {
    "ಕ್ಕೆ": ("ಗೆ", "ಕ್ಕೆ"),
    "ರಲ್ಲಿ": ("ಯಲ್ಲಿ", "ದಲ್ಲಿ"),
    "ರೊಳಗೆ": ("ಯೊಳಗೆ", "ದೊಳಗೆ"),
    "ರವರೆಗೆ": ("ಯವರೆಗೆ", "ದವರೆಗೆ"),
}


class VerbalizeFst(GraphFst):
    """
    Union of all per-class ITN verbalizer grammars.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize", kind="verbalize", deterministic=deterministic)

        self.fst = (
            generic.CardinalFst(deterministic=deterministic).fst
            | generic.DecimalFst(deterministic=deterministic).fst
            | generic.FractionFst(deterministic=deterministic).fst
            | generic.OrdinalFst(deterministic=deterministic).fst
            | generic.DateFst(deterministic=deterministic).fst
            | generic.TimeFst(
                duration_nouns=DURATION_NOUNS,
                duration_suffixes=DURATION_SUFFIXES,
                deterministic=deterministic,
            ).fst
            | generic.MoneyFst(deterministic=deterministic).fst
            | generic.TelephoneFst(deterministic=deterministic).fst
        )
