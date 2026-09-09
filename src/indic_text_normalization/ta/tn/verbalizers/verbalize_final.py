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

from indic_text_normalization.ta.constants import (
    GraphFst,
    delete_extra_space,
    delete_space,
)
from indic_text_normalization.ta.tn.verbalizers.verbalize import VerbalizeFst
from indic_text_normalization.ta.tn.verbalizers.word import WordFst


class VerbalizeFinalFst(GraphFst):
    """
    Finite state transducer that verbalizes an entire tagged sentence, e.g.
    tokens { time { hours: "பத்து" minutes: "முப்பது" } } -> பத்து மணி முப்பது நிமிடம்.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize_final", kind="verbalize", deterministic=deterministic)

        types = (
            VerbalizeFst(deterministic=deterministic).fst | WordFst(deterministic=deterministic).fst
        )
        graph = (
            pynutil.delete("tokens")
            + delete_space
            + pynutil.delete("{")
            + delete_space
            + types
            + delete_space
            + pynutil.delete("}")
        )
        graph = delete_space + pynini.closure(graph + delete_extra_space) + graph + delete_space

        self.fst = graph.optimize()
