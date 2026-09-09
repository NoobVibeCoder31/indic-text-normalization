# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from indic_text_normalization.ta.constants import GraphFst
from indic_text_normalization.ta.tn.verbalizers.cardinal import CardinalFst
from indic_text_normalization.ta.tn.verbalizers.date import DateFst
from indic_text_normalization.ta.tn.verbalizers.decimal import DecimalFst
from indic_text_normalization.ta.tn.verbalizers.fraction import FractionFst
from indic_text_normalization.ta.tn.verbalizers.measure import MeasureFst
from indic_text_normalization.ta.tn.verbalizers.money import MoneyFst
from indic_text_normalization.ta.tn.verbalizers.ordinal import OrdinalFst
from indic_text_normalization.ta.tn.verbalizers.range import RangeFst
from indic_text_normalization.ta.tn.verbalizers.telephone import TelephoneFst
from indic_text_normalization.ta.tn.verbalizers.time import TimeFst
from indic_text_normalization.ta.tn.verbalizers.whitelist import WhiteListFst


class VerbalizeFst(GraphFst):
    """
    Union of all per-class verbalizer grammars.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize", kind="verbalize", deterministic=deterministic)

        cardinal = CardinalFst(deterministic=deterministic)
        decimal = DecimalFst(deterministic=deterministic)
        time = TimeFst()
        date = DateFst(deterministic=deterministic)
        money = MoneyFst()
        measure = MeasureFst(deterministic=deterministic)
        number_range = RangeFst(deterministic=deterministic)
        fraction = FractionFst(deterministic=deterministic)
        ordinal = OrdinalFst(deterministic=deterministic)
        telephone = TelephoneFst(deterministic=deterministic)
        whitelist = WhiteListFst(deterministic=deterministic)

        self.fst = (
            cardinal.fst
            | decimal.fst
            | time.fst
            | date.fst
            | money.fst
            | measure.fst
            | number_range.fst
            | fraction.fst
            | ordinal.fst
            | telephone.fst
            | whitelist.fst
        )
