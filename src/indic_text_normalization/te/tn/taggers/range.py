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

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst, attach_case_suffix


class RangeFst(GraphFst):
    """
    Finite state transducer for classifying numeric ranges, e.g.
        10-20 -> range { lower: "పది" upper: "ఇరవై" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="range", kind="classify", deterministic=deterministic)

        graph = (
            pynutil.insert('lower: "')
            + cardinal.final_graph
            + pynutil.insert('"')
            + pynutil.delete(pynini.closure(" ", 0, 1) + "-" + pynini.closure(" ", 0, 1))
            + pynutil.insert(' upper: "')
            + (
                cardinal.final_graph
                | pynutil.add_weight(attach_case_suffix(cardinal.final_graph), 0.1)
            )
            + pynutil.insert('"')
            + pynutil.insert(" preserve_order: true")
        )
        self.fst = self.add_tokens(graph).optimize()
