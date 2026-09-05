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

from indic_text_normalization.ta.constants import CHAR, GraphFst
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst


class OrdinalFst(GraphFst):
    """
    Finite state transducer for classifying Tamil ordinals, e.g.
        5வது -> ordinal { integer: "ஐந்தாவது" }
        ௧௦ஆம் -> ordinal { integer: "பத்தாம்" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="classify", deterministic=deterministic)

        # The adjectival stem replaces the cardinal's final -உ (or -ம்) with -ஆ:
        # ஐந்து -> ஐந்தா, ஆயிரம் -> ஆயிரமா.
        ending_to_aa = pynini.union(pynini.cross("ு", "ா"), pynini.cross("ம்", "மா"))
        stem = cardinal.final_graph @ (pynini.closure(CHAR) + ending_to_aa)

        # முதல் is the idiomatic stem for first.
        first = pynini.cross("௧", "முதலா") | pynini.cross("1", "முதலா")
        stem = pynini.union(stem, pynutil.add_weight(first, -0.1))

        suffix_vathu = pynutil.delete(pynini.union("வது", "ஆவது", "-வது")) + pynutil.insert("வது")
        suffix_aam = pynutil.delete("ஆம்") + pynutil.insert("ம்")

        graph = stem + pynini.union(suffix_vathu, suffix_aam)

        final_graph = pynutil.insert('integer: "') + graph + pynutil.insert('"')
        self.fst = self.add_tokens(final_graph).optimize()
