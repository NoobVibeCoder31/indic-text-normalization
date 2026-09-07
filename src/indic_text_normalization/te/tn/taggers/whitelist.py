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

from indic_text_normalization.te.constants import (
    SIGMA,
    GraphFst,
    convert_space,
)
from indic_text_normalization.te.utils import get_abs_path
from indic_text_normalization.core.utils import load_labels


class WhiteListFst(GraphFst):
    """
    Finite state transducer for classifying whitelist entries, e.g.
        డా. -> tokens { name: "డాక్టర్" }
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="whitelist", kind="classify", deterministic=deterministic)

        def _whitelist_graph(file: str) -> pynini.Fst:
            rows = [row for row in load_labels(file) if len(row) >= 2]
            return pynini.string_map([(x, y) for x, y, *_ in rows])

        graph = _whitelist_graph(get_abs_path("data/whitelist/abbreviations.tsv"))
        graph |= pynini.compose(
            pynini.difference(SIGMA, pynini.accep("/")).optimize(),
            _whitelist_graph(get_abs_path("data/whitelist/symbol.tsv")),
        ).optimize()

        self.graph = convert_space(graph).optimize()
        self.fst = (pynutil.insert('name: "') + self.graph + pynutil.insert('"')).optimize()
