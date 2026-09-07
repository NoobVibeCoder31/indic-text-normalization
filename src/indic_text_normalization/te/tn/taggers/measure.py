# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
# Copyright 2015 and onwards Google, Inc.
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

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import load_labels
from indic_text_normalization.te.constants import (
    CASE_SUFFIXES,
    POINT_WORD,
    TO_LOWER,
    GraphFst,
    convert_space,
    delete_zero_or_one_space,
)
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst
from indic_text_normalization.te.tn.taggers.decimal import DecimalFst
from indic_text_normalization.te.tn.taggers.money import RANGE_WORD
from indic_text_normalization.te.utils import get_abs_path

# ID-prone letters (bus route 47A, model 570X...) swallow alphanumeric IDs when glued
# to the number, so those match only after an explicit space.
ID_PRONE = frozenset("ABCGJKNVWXbdhqsx*")


class MeasureFst(GraphFst):
    """
    Finite state transducer for classifying measures, e.g.
        5 కి.మీ. -> measure { amount: "ఐదు" units: "కిలోమీటర్" }
        12.5kg -> measure { amount: "పన్నెండు దశాంశం ఐదు" units: "కిలోగ్రామ్" }
    The unit travels in its singular form; the verbalizer picks singular or plural.
    """

    def __init__(
        self, cardinal: CardinalFst, decimal: DecimalFst, deterministic: bool = True
    ) -> None:
        super().__init__(name="measure", kind="classify", deterministic=deterministic)

        rows = [r for r in load_labels(get_abs_path("data/measure/unit.tsv")) if len(r) >= 2]
        multi = pynini.string_map(
            [(k, v) for k, v, *_ in rows if len(k) > 1 or k not in ID_PRONE]
        ).optimize()
        single = pynini.string_map([(k, v) for k, v, *_ in rows if len(k) == 1]).optimize()

        # Accept uppercase spellings of Latin units (5KG).
        lowercase = pynini.closure(TO_LOWER | pynini.union(*"abcdefghijklmnopqrstuvwxyz°²./"), 2)
        multi |= pynini.compose(lowercase, multi).optimize()

        unit_multi = convert_space(multi).optimize()
        unit_single = convert_space(single).optimize()

        amount = pynini.union(
            cardinal.final_graph,
            cardinal.final_graph + pynini.cross(".", f" {POINT_WORD} ") + decimal.graph,
        ).optimize()
        # 5-10 kg reads as a range amount.
        amount = pynini.union(
            amount, amount + pynini.cross("-", f" {RANGE_WORD} ") + amount
        ).optimize()

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
            + pynini.closure(
                pynutil.insert(' suffix: "') + pynini.union(*CASE_SUFFIXES) + pynutil.insert('"'),
                0,
                1,
            )
            + pynutil.insert(" preserve_order: true")
        )
        self.fst = self.add_tokens(graph).optimize()
