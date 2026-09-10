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

"""
TN verbalizers whose output is the tagged value itself, shared by every language.

A class whose spoken form needs the language's morphology (money, measure, time, decimal,
fraction) keeps its verbalizer in the language package.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    CHAR,
    MIN_NEG_WEIGHT,
    NOT_QUOTE,
    SIGMA,
    SPACE,
    GraphFst,
    delete_preserve_order,
    delete_space,
    insert_space,
)

_NBSP_TO_SPACE = pynini.cdrewrite(pynini.cross("\u00a0", " "), "", "", SIGMA)


def _field(name: str) -> pynini.Fst:
    """
    Consume ``name: "value"``, emitting the value.
    """
    return pynutil.delete(f'{name}: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')


class CardinalFst(GraphFst):
    """
    Finite state transducer for verbalizing cardinals, e.g.
        cardinal { negative: "true" integer: "இருபத்துமூன்று" } -> மைனஸ் இருபத்துமூன்று

    Attributes
    ----------
    minus_word : ``str``
        Spoken form of a leading minus sign.
    plus_word : ``str``
        Spoken form of a leading plus sign.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(self, *, minus_word: str, plus_word: str, deterministic: bool = True) -> None:
        super().__init__(name="cardinal", kind="verbalize", deterministic=deterministic)

        sign = pynini.cross('negative: "true"', f"{minus_word} ") | pynini.cross(
            'positive: "true"', f"{plus_word} "
        )
        self.optional_sign = pynini.closure(sign + delete_space, 0, 1)
        self.integer = (
            delete_space + pynutil.delete('"') + pynini.closure(NOT_QUOTE) + pynutil.delete('"')
        )
        self.numbers = self.optional_sign + pynutil.delete("integer:") + self.integer
        self.fst = self.delete_tokens(self.numbers).optimize()


class DateFst(GraphFst):
    """
    Finite state transducer for verbalizing dates, e.g.
        date { day: "ஒன்று" month: "ஏப்ரல்" year: "..." } -> ஒன்று ஏப்ரல் ...
        date { year: "..." month: "ஜனவரி" day: "பதினைந்து" } -> ... ஜனவரி பதினைந்து
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="date", kind="verbalize", deterministic=deterministic)

        day, month, year, era = _field("day"), _field("month"), _field("year"), _field("era")
        graph = (
            day + SPACE + month
            | month + SPACE + day
            | day + SPACE + month + SPACE + year
            | month + SPACE + day + SPACE + year
            | year + SPACE + month + SPACE + day
            | era
        )
        self.graph = graph + delete_space + delete_preserve_order
        self.fst = self.delete_tokens(self.graph).optimize()


class OrdinalFst(GraphFst):
    """
    Finite state transducer for verbalizing ordinals, e.g.
        ordinal { integer: "பத்தாவது" } -> பத்தாவது
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="verbalize", deterministic=deterministic)

        self.fst = self.delete_tokens(_field("integer")).optimize()


class RangeFst(GraphFst):
    """
    Finite state transducer for verbalizing ranges, e.g.
        range { lower: "பத்து" upper: "இருபது" } -> பத்து முதல் இருபது

    Attributes
    ----------
    range_word : ``str``
        Word spoken between the two bounds.
    range_suffix : ``str``, optional (default = "")
        Word spoken after the upper bound (Malayalam വരെ).
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self, *, range_word: str, range_suffix: str = "", deterministic: bool = True
    ) -> None:
        super().__init__(name="range", kind="verbalize", deterministic=deterministic)

        tail = f" {range_suffix}" if range_suffix else ""
        graph = (
            _field("lower")
            + delete_space
            + pynutil.insert(f" {range_word} ")
            + _field("upper")
            + pynutil.insert(tail)
            + delete_preserve_order
        )
        self.fst = self.delete_tokens(graph).optimize()


class TelephoneFst(GraphFst):
    """
    Finite state transducer for verbalizing telephone numbers, e.g.
        telephone { country_code: "பிளஸ் ஒன்பது ஒன்று" number_part: "ஒன்பது ..." } -> பிளஸ் ஒன்பது ஒன்று ஒன்பது ...
        telephone { country_code: "பிளஸ் ஒன்பது ஒன்று" } -> பிளஸ் ஒன்பது ஒன்று
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="verbalize", deterministic=deterministic)

        country_code = _field("country_code")
        optional_country_code = pynini.closure(country_code + delete_space + insert_space, 0, 1)
        number_part = (
            pynutil.delete('number_part: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynini.closure(pynutil.add_weight(pynutil.delete(SPACE), MIN_NEG_WEIGHT), 0, 1)
            + pynutil.delete('"')
        )
        optional_extension = pynini.closure(delete_space + insert_space + _field("extension"), 0, 1)
        graph = (optional_country_code + number_part + optional_extension) | country_code
        self.fst = self.delete_tokens(graph).optimize()


class WhiteListFst(GraphFst):
    """
    Finite state transducer for verbalizing whitelist entries, e.g.
        tokens { name: "டாக்டர்" } -> டாக்டர்
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="whitelist", kind="verbalize", deterministic=deterministic)

        graph = (
            pynutil.delete("name:")
            + delete_space
            + pynutil.delete('"')
            + pynini.closure(CHAR - " ", 1)
            + pynutil.delete('"')
        )
        # Multi-word values travel with U+00A0 NO-BREAK SPACE; speak them with plain spaces.
        self.fst = (graph @ _NBSP_TO_SPACE).optimize()


class WordFst(GraphFst):
    """
    Finite state transducer for verbalizing plain words, e.g.
        tokens { name: "தமிழ்" } -> தமிழ்
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="word", kind="verbalize", deterministic=deterministic)

        chars = pynini.closure(CHAR - " ", 1)
        punct = pynini.union("!", "?", ".", ",", "-", ":", ";", "।")
        char = (
            pynutil.delete("name:")
            + delete_space
            + pynutil.delete('"')
            + chars
            + pynutil.delete('"')
        )
        # A mark following a word attaches to it without a space.
        graph = char + pynini.closure(delete_space + punct, 0, 1)
        graph = graph @ pynini.cdrewrite(pynini.cross(" ", ""), "", punct, SIGMA)
        # Multi-word values travel with U+00A0 NO-BREAK SPACE; speak them with plain spaces.
        self.fst = (graph @ _NBSP_TO_SPACE).optimize()
