"""
Union of all Telugu ITN per-class verbalizers.
"""

from indic_text_normalization.core import itn_verbalizers as generic
from indic_text_normalization.core.graph_utils import GraphFst

# Nouns restored after an hour above 23, which is a duration rather than a clock time.
DURATION_NOUNS = ("గంటల", "నిమిషాలు")


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
            | generic.TimeFst(duration_nouns=DURATION_NOUNS, deterministic=deterministic).fst
            | generic.MoneyFst(deterministic=deterministic).fst
            | generic.TelephoneFst(deterministic=deterministic).fst
        )
