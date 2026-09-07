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

from indic_text_normalization.te.constants import (
    ASCII_TO_TE_NUMBER,
    DIGIT,
    POINT_WORD,
    TE_DIGIT,
    GraphFst,
    insert_space,
)
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst, attach_case_suffix

# Scale words that may follow a number (5 లక్షలు, 1.5 కోట్లు, 2 lakh, 5 million).
_TE_QUANTITIES = [
    "వందలు",
    "వందల",
    "వెయ్యి",
    "వేలు",
    "వేల",
    "లక్ష",
    "లక్షం",
    "లక్షలు",
    "లక్షల",
    "కోటి",
    "కోట్లు",
    "కోట్ల",
    "మిలియన్",
    "మిలియన్లు",
    "బిలియన్",
    "బిలియన్లు",
    "ట్రిలియన్",
    "ట్రిలియన్లు",
]
_EN_QUANTITIES = {
    "thousand": "వేలు",
    "lakh": "లక్షలు",
    "lakhs": "లక్షలు",
    "crore": "కోట్లు",
    "crores": "కోట్లు",
    "million": "మిలియన్",
    "billion": "బిలియన్",
    "trillion": "ట్రిలియన్",
}
quantities = pynini.union(
    pynini.union(*_TE_QUANTITIES),
    pynini.string_map(list(_EN_QUANTITIES.items())),
).optimize()

any_digit = pynini.union(DIGIT, TE_DIGIT)
delete_commas = (
    any_digit + pynini.closure(pynini.closure(pynutil.delete(","), 0, 1) + any_digit)
).optimize()


def get_quantity(decimal: "pynini.FstLike", cardinal_graph: "pynini.FstLike") -> "pynini.FstLike":
    """
    Returns FST that transforms either a cardinal or decimal followed by a quantity into a numeral,
    e.g. ౧ లక్ష -> integer_part: "ఒకటి" quantity: "లక్ష"
    e.g. ౧.౫ లక్షలు -> integer_part: "ఒకటి" fractional_part: "ఐదు" quantity: "లక్షలు"
    """
    quantity = (
        pynutil.delete(" ")
        + insert_space
        + pynutil.insert('quantity: "')
        + quantities
        + pynutil.insert('"')
    )
    res = pynutil.insert('integer_part: "') + cardinal_graph + pynutil.insert('"') + quantity
    res |= decimal + quantity
    return res


class DecimalFst(GraphFst):
    """
    Finite state transducer for classifying decimal, e.g.
        -౧౨.౫౦౦౬ కోట్లు -> decimal { negative: "true" integer_part: "పన్నెండు"  fractional_part: "ఐదు సున్నా సున్నా ఆరు" quantity: "కోట్లు" }
        ౧ కోటి -> decimal { integer_part: "ఒకటి" quantity: "కోటి" }

    cardinal: CardinalFst
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="classify", deterministic=deterministic)

        graph_digit = cardinal.digit | cardinal.zero
        cardinal_graph = cardinal.final_graph

        te_digit_sequence = (graph_digit + pynini.closure(insert_space + graph_digit)).optimize()
        arabic_digit_sequence = pynini.compose(
            pynini.closure(DIGIT, 1), ASCII_TO_TE_NUMBER @ te_digit_sequence
        ).optimize()
        self.graph = (te_digit_sequence | arabic_digit_sequence).optimize()

        point = pynutil.delete(".")

        optional_graph_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true"') + insert_space,
            0,
            1,
        )

        integer_with_commas = pynini.compose(delete_commas, cardinal_graph).optimize()
        integer_graph = pynutil.add_weight(integer_with_commas, -0.1) | cardinal_graph

        self.graph_fractional = (
            pynutil.insert('fractional_part: "')
            + (self.graph | pynutil.add_weight(attach_case_suffix(self.graph), 0.1))
            + pynutil.insert('"')
        )
        self.graph_integer = pynutil.insert('integer_part: "') + integer_graph + pynutil.insert('"')

        final_graph_wo_sign = self.graph_integer + point + insert_space + self.graph_fractional

        # Bare-dot decimals: .5 reads as సున్నా దశాంశం ఐదు.
        bare_dot = (
            pynutil.insert('integer_part: "సున్నా"') + point + insert_space + self.graph_fractional
        )
        # Dotted chains (versions, IPs): every segment after the first reads
        # digit-by-digit with దశాంశం between them.
        dotted_chain = (
            self.graph_integer
            + point
            + insert_space
            + pynutil.insert('fractional_part: "')
            + self.graph
            + pynini.closure(pynini.cross(".", f" {POINT_WORD} ") + self.graph, 1)
            + pynutil.insert('"')
        )
        final_graph_wo_sign |= pynutil.add_weight(bare_dot, 0.1)
        final_graph_wo_sign |= pynutil.add_weight(dotted_chain, 0.5)

        self.final_graph_wo_negative = final_graph_wo_sign | get_quantity(
            final_graph_wo_sign, integer_graph
        )

        final_graph = optional_graph_negative + self.final_graph_wo_negative
        self.fst = self.add_tokens(final_graph).optimize()
