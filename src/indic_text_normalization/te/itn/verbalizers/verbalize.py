"""
Union of all Telugu ITN per-class verbalizers.
"""

from indic_text_normalization.te.constants import GraphFst
from indic_text_normalization.te.itn.verbalizers.cardinal import CardinalFst
from indic_text_normalization.te.itn.verbalizers.date import DateFst
from indic_text_normalization.te.itn.verbalizers.decimal import DecimalFst
from indic_text_normalization.te.itn.verbalizers.fraction import FractionFst
from indic_text_normalization.te.itn.verbalizers.money import MoneyFst
from indic_text_normalization.te.itn.verbalizers.ordinal import OrdinalFst
from indic_text_normalization.te.itn.verbalizers.telephone import TelephoneFst
from indic_text_normalization.te.itn.verbalizers.time import TimeFst


class VerbalizeFst(GraphFst):
    """
    Union of all per-class ITN verbalizer grammars.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize", kind="verbalize", deterministic=deterministic)

        self.fst = (
            CardinalFst(deterministic=deterministic).fst
            | DecimalFst(deterministic=deterministic).fst
            | FractionFst(deterministic=deterministic).fst
            | OrdinalFst(deterministic=deterministic).fst
            | DateFst(deterministic=deterministic).fst
            | TimeFst(deterministic=deterministic).fst
            | MoneyFst(deterministic=deterministic).fst
            | TelephoneFst(deterministic=deterministic).fst
        )
