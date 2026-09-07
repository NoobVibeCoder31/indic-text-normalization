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

from indic_text_normalization.te.constants import GraphFst
from indic_text_normalization.te.tn.taggers.cardinal import (
    ORDINAL_TAILS,
    CardinalFst,
    ordinal_graph,
)


class OrdinalFst(GraphFst):
    """
    Finite state transducer for classifying Telugu ordinals, e.g.
        5వ -> ordinal { integer: "ఐదవ" }
        1వ -> ordinal { integer: "మొదటి" }
        ౨౧వది -> ordinal { integer: "ఇరవై ఒకటవది" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="classify", deterministic=deterministic)

        graph = ordinal_graph(cardinal.final_graph)

        # మొదటి is the idiomatic word for first; an inflected tail still attaches (1వది).
        tails = pynini.union(*[pynini.accep(t) for t in ORDINAL_TAILS])
        first = (
            pynini.union(pynini.cross("౧", "మొదటి"), pynini.cross("1", "మొదటి"))
            + pynutil.delete("వ")
            + tails
        )
        graph = pynini.union(graph, pynutil.add_weight(first, -0.1))

        final_graph = pynutil.insert('integer: "') + graph + pynutil.insert('"')
        self.fst = self.add_tokens(final_graph).optimize()
