"""
Union of all Malayalam TN per-class verbalizers.
"""

from indic_text_normalization.core import tn_verbalizers as generic
from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.ml.constants import MINUS_WORD, PLUS_WORD, RANGE_SUFFIX, RANGE_WORD
from indic_text_normalization.ml.tn.verbalizers.decimal import DecimalFst
from indic_text_normalization.ml.tn.verbalizers.fraction import FractionFst
from indic_text_normalization.ml.tn.verbalizers.measure import MeasureFst
from indic_text_normalization.ml.tn.verbalizers.money import MoneyFst
from indic_text_normalization.ml.tn.verbalizers.time import TimeFst


class VerbalizeFst(GraphFst):
    """
    Union of all per-class TN verbalizer grammars.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize", kind="verbalize", deterministic=deterministic)

        self.fst = (
            generic.CardinalFst(minus_word=MINUS_WORD, plus_word=PLUS_WORD).fst
            | DecimalFst(deterministic=deterministic).fst
            | TimeFst(deterministic=deterministic).fst
            | generic.DateFst(deterministic=deterministic).fst
            | MoneyFst(deterministic=deterministic).fst
            | MeasureFst(deterministic=deterministic).fst
            | generic.RangeFst(range_word=RANGE_WORD, range_suffix=RANGE_SUFFIX).fst
            | FractionFst(deterministic=deterministic).fst
            | generic.OrdinalFst(deterministic=deterministic).fst
            | generic.TelephoneFst(deterministic=deterministic).fst
            | generic.WhiteListFst(deterministic=deterministic).fst
        )
