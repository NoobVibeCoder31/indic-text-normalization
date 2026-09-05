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

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import load_labels
from indic_text_normalization.ta.constants import (
    TO_LOWER,
    GraphFst,
    convert_space,
    delete_zero_or_one_space,
)
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.ta.tn.taggers.decimal import DecimalFst
from indic_text_normalization.ta.utils import get_abs_path


class MeasureFst(GraphFst):
    """
    Finite state transducer for classifying measures, e.g.
        5 கி.மீ. -> measure { amount: "ஐந்து" units: "கிலோமீட்டர்" }
        12.5kg -> measure { amount: "பன்னிரண்டு புள்ளி ஐந்து" units: "கிலோகிராம்" }
    """

    def __init__(
        self, cardinal: CardinalFst, decimal: DecimalFst, deterministic: bool = True
    ) -> None:
        super().__init__(name="measure", kind="classify", deterministic=deterministic)

        rows = [r for r in load_labels(get_abs_path("data/measure/unit.tsv")) if len(r) >= 2]
        # ID-prone letters (bus route 47A, model 570X...) swallow alphanumeric IDs
        # when glued to the number, so those match only after an explicit space.
        id_prone = {"A", "B", "C", "J", "K", "N", "V", "W", "X", "b", "d", "h", "q", "s", "x", "*"}
        multi = pynini.string_map(
            [(k, v) for k, v, *_ in rows if len(k) > 1 or k not in id_prone]
        ).optimize()
        single = pynini.string_map([(k, v) for k, v, *_ in rows if len(k) == 1]).optimize()

        # Accept uppercase spellings of Latin units (5KG).
        lowercase = pynini.closure(TO_LOWER | pynini.union(*"abcdefghijklmnopqrstuvwxyz°²./"), 1)
        multi |= pynini.compose(lowercase, multi).optimize()

        unit_multi = convert_space(multi).optimize()
        unit_single = convert_space(single).optimize()

        amount = pynini.union(
            cardinal.final_graph,
            cardinal.final_graph + pynini.cross(".", " புள்ளி ") + decimal.graph,
        ).optimize()
        # 5-10 kg reads as a range amount.
        amount = pynini.union(amount, amount + pynini.cross("-", " முதல் ") + amount).optimize()

        optional_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" '), 0, 1
        )

        unit_part = (delete_zero_or_one_space + unit_multi) | (pynutil.delete(" ") + unit_single)

        graph = (
            optional_negative
            + pynutil.insert('amount: "')
            + amount
            + pynutil.insert('"')
            + pynutil.insert(' units: "')
            + unit_part
            + pynutil.insert('"')
            + pynutil.insert(" preserve_order: true")
        )
        self.fst = self.add_tokens(graph).optimize()
