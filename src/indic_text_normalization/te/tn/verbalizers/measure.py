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
    MINUS_WORD,
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
    insert_space,
)
from indic_text_normalization.te.morphology import (
    MANY,
    NBSP_TO_SPACE,
    OBLIQUE_FINAL,
    ONE_AS_OKA,
    optional_suffix_field,
    suffix_sandhi,
)
from indic_text_normalization.te.utils import get_abs_path


class MeasureFst(GraphFst):
    """
    Finite state transducer for verbalizing measures, e.g.
        measure { amount: "ఐదు" units: "కిలోమీటర్" } -> ఐదు కిలోమీటర్లు
        measure { amount: "ఒకటి" units: "కిలోమీటర్" } -> ఒక కిలోమీటర్
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="measure", kind="verbalize", deterministic=deterministic)

        optional_sign = pynini.closure(
            pynini.cross('negative: "true"', f"{MINUS_WORD} ") + delete_space, 0, 1
        )
        # The tagger carries the singular unit (with U+00A0 inside multi-word values);
        # a count other than one takes the plural column of the unit table.
        rows = [r for r in load_labels(get_abs_path("data/measure/unit.tsv")) if len(r) >= 3]
        nbsp = " "
        plural_pairs = {(sg.replace(" ", nbsp), pl.replace(" ", nbsp)) for _, sg, pl in rows}
        pluralize = pynini.string_map(sorted(plural_pairs)).optimize()
        singular = pynini.closure(NOT_QUOTE, 1)

        amount_one = pynutil.delete('amount: "') + ONE_AS_OKA + pynutil.delete('"')
        amount_many = pynutil.delete('amount: "') + (MANY @ OBLIQUE_FINAL) + pynutil.delete('"')
        units_singular = pynutil.delete('units: "') + singular + pynutil.delete('"')
        units_plural = pynutil.delete('units: "') + (singular @ pluralize) + pynutil.delete('"')

        graph = optional_sign + (
            amount_one + delete_space + insert_space + units_singular
            | amount_many + delete_space + insert_space + units_plural
        )
        graph = (graph + optional_suffix_field() + delete_preserve_order) @ NBSP_TO_SPACE
        graph = graph @ suffix_sandhi()
        self.fst = self.delete_tokens(graph).optimize()
