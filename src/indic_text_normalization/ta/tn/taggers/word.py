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
    ALPHA,
    MIN_NEG_WEIGHT,
    NOT_SPACE,
    TA_BLOCK,
    GraphFst,
    convert_space,
)
from indic_text_normalization.ta.tn.taggers.punctuation import PunctuationFst


class WordFst(GraphFst):
    """
    Finite state transducer for classifying Tamil words.
        e.g. தமிழ் -> tokens { name: "தமிழ்" }

    Args:
        punctuation: PunctuationFst
        deterministic: if True will provide a single transduction option,
            for False multiple transductions are generated (used for audio-based normalization)
    """

    def __init__(self, punctuation: PunctuationFst, deterministic: bool = True):
        super().__init__(name="word", kind="classify", deterministic=deterministic)

        # Include punctuation in the graph
        # pynini.Fst.project mutates in place and returns self, so project a copy:
        # punctuation.graph is shared with the tokenizer, which needs it unprojected.
        punct = punctuation.graph.copy().project("input").optimize()
        default_graph = pynini.closure(pynini.difference(NOT_SPACE, punct), 1)
        symbols_to_exclude = (pynini.union("$", "€", "₩", "£", "¥", "#", "%") | punct).optimize()

        # Use TAMIL_CHAR in the graph
        graph = pynini.closure(pynini.difference(TA_BLOCK, symbols_to_exclude), 1)
        graph = pynutil.add_weight(graph, MIN_NEG_WEIGHT) | default_graph

        # URLs stay whole instead of being split into punctuation tokens.
        url_body = pynini.closure(pynini.difference(NOT_SPACE, pynini.accep('"')), 1)
        url = (pynini.closure(ALPHA, 1) + "://" + url_body) | ("www." + url_body)
        graph = pynutil.add_weight(url, MIN_NEG_WEIGHT) | graph

        # Ensure no spaces around punctuation
        graph = pynini.closure(graph + pynini.closure(punct + graph, 0, 1))

        self.graph = convert_space(graph)
        self.fst = (pynutil.insert('name: "') + self.graph + pynutil.insert('"')).optimize()
