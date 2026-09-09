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
from indic_text_normalization.ta.constants import NOT_QUOTE, SIGMA, SPACE, GraphFst
from indic_text_normalization.ta.utils import get_abs_path

# Single source of truth for both directions; ITN inverts these same pairs.
major_minor_currencies = dict(
    load_labels(get_abs_path("data/money/major_minor_currencies.tsv"), min_fields=2)
)


class MoneyFst(GraphFst):
    """
    Finite state transducer for verbalizing money, e.g.
        money { integer_part: "பன்னிரண்டு" currency_maj: "ரூபாய்" } -> பன்னிரண்டு ரூபாய்
        money { integer_part: "பன்னிரண்டு" currency_maj: "ரூபாய்" fractional_part: "ஐம்பது" currency_min: "centiles" } -> பன்னிரண்டு ரூபாய் ஐம்பது பைசா
        money { currency_maj: "ரூபாய்" integer_part: "பூஜ்யம்" fractional_part: "ஐம்பது" currency_min: "centiles" } -> ஐம்பது பைசா

    Args:
        cardinal: CardinalFst
        decimal: DecimalFst
        deterministic: if True will provide a single transduction option,
            for False multiple transduction are generated (used for audio-based normalization)
    """

    def __init__(self) -> None:
        super().__init__(name="money", kind="verbalize")

        # A case suffix on the amount attaches to the currency word; the sandhi
        # rewrite below joins ரூபாய் + ஆக -> ரூபாயாக and ரூபாய் + இல் -> ரூபாயில்.
        optional_suffix = pynini.closure(
            pynutil.delete(' suffix: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"'), 0, 1
        )
        currency_major = (
            pynutil.delete('currency_maj: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
            + optional_suffix
        )

        # A whole-field ஒன்று — or ஒன்று heading a quantity phrase (ஒரு லட்சம்) — reads
        # as ஒரு, but not before a decimal point (ஒன்று புள்ளி ஐந்து கோடி).
        not_point = pynini.difference(
            pynini.closure(NOT_QUOTE, 1), pynini.accep("புள்ளி") + pynini.closure(NOT_QUOTE)
        )
        one_phrase = (pynini.accep("ஒன்று") + pynini.closure(" " + not_point, 0, 1)).optimize()
        one_as_oru = pynini.cross("ஒன்று", "ஒரு") + pynini.closure(
            " " + not_point, 0, 1
        ) | pynini.difference(pynini.closure(NOT_QUOTE, 1), one_phrase)
        integer_part = pynutil.delete('integer_part: "') + one_as_oru + pynutil.delete('"')

        fractional_part = pynutil.delete('fractional_part: "') + one_as_oru + pynutil.delete('"')

        # Handles major denominations only
        graph_major_only = integer_part + pynini.accep(SPACE) + currency_major

        # Handles both major and minor denominations
        major_minor_graphs = []

        # Handles minor denominations only
        minor_graphs = []

        # Logic for handling minor denominations
        for major, minor in major_minor_currencies.items():
            graph_major = (
                pynutil.delete('currency_maj: "') + pynini.accep(major) + pynutil.delete('"')
            )
            graph_minor = (
                pynutil.delete('currency_min: "')
                + pynini.cross("centiles", minor)
                + pynutil.delete('"')
            )
            graph_major_minor_partial = (
                integer_part
                + pynini.accep(SPACE)
                + graph_major
                + pynini.accep(SPACE)
                + fractional_part
                + pynini.accep(SPACE)
                + graph_minor
            )
            major_minor_graphs.append(graph_major_minor_partial)

            graph_minor_partial = (
                pynutil.delete('integer_part: "பூஜ்யம்"')
                + pynutil.delete(SPACE)
                + pynutil.delete('currency_maj: "')
                + pynutil.delete(major)
                + pynutil.delete('"')
                + pynutil.delete(SPACE)
                + fractional_part
                + pynini.accep(SPACE)
                + graph_minor
            )
            minor_graphs.append(graph_minor_partial)

        graph_major_minor = pynini.union(*major_minor_graphs)
        graph_minor_only = pynini.union(*minor_graphs)

        graph = graph_major_only | graph_major_minor | pynutil.add_weight(graph_minor_only, -0.1)

        optional_sign = pynini.closure(pynini.cross('negative: "true" ', "மைனஸ் "), 0, 1)
        graph = optional_sign + graph
        suffix_sandhi = pynini.cdrewrite(
            pynini.union(pynini.cross("்ஆ", "ா"), pynini.cross("்இ", "ி")), "", "", SIGMA
        )
        graph = graph @ suffix_sandhi

        delete_tokens = self.delete_tokens(graph)
        self.fst = delete_tokens.optimize()
