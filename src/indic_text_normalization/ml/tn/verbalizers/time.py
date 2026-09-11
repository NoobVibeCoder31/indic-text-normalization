"""
Malayalam TN time verbalizer.
"""

import pynini

from indic_text_normalization.core.tn_verbalizers import InvariantTimeFst
from indic_text_normalization.ml.constants import LANG
from indic_text_normalization.ml.morphology import (
    NOT_ONE,
    ONE_AS_ORU,
    optional_suffix_field,
    suffix_sandhi,
)


class TimeFst(InvariantTimeFst):
    """
    Clock times with invariant nouns, the counting ഒരു and the day part by hour:
        time { hours: "പത്ത്" minutes: "ഒന്ന്" } -> പത്ത് മണി ഒരു മിനിറ്റ്
        time { hours: "പത്ത്" suffix: "ന്" } -> പത്ത് മണിക്ക്
        time { hours: "പത്ത്" meridiem: "PM" } -> രാത്രി പത്ത് മണി
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(
            lang=LANG,
            nouns=("മണി", "മിനിറ്റ്", "സെക്കൻഡ്"),
            count=pynini.union(ONE_AS_ORU, NOT_ONE),
            suffix_field=optional_suffix_field(),
            sandhi=suffix_sandhi(),
            deterministic=deterministic,
        )
