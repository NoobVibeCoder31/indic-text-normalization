"""
Malayalam TN money verbalizer.
"""

import pynini

from indic_text_normalization.core.tn_verbalizers import InvariantMoneyFst
from indic_text_normalization.ml.constants import LANG, MINUS_WORD
from indic_text_normalization.ml.morphology import (
    NOT_ONE,
    ONE_AS_ORU,
    fuse_thousand,
    one_before_scale,
    optional_suffix_field,
    suffix_sandhi,
)


class MoneyFst(InvariantMoneyFst):
    """
    Money with invariant currency nouns and the counting ഒരു:
        money { integer_part: "ഒന്ന്" currency_maj: "രൂപ" } -> ഒരു രൂപ
        money { integer_part: "അഞ്ച് കോടി" currency_maj: "രൂപ" suffix: "ന്" } -> അഞ്ച് കോടി രൂപയ്ക്ക്
        money { integer_part: "അഞ്ച് ആയിരം" currency_maj: "രൂപ" } -> അഞ്ചായിരം രൂപ
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            lang=LANG,
            minus_word=MINUS_WORD,
            amount=pynini.union(ONE_AS_ORU, NOT_ONE @ one_before_scale() @ fuse_thousand()),
            zero_word="പൂജ്യം",
            suffix_field=optional_suffix_field(),
            sandhi=suffix_sandhi(),
            deterministic=deterministic,
        )
