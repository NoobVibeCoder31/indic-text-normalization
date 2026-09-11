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


def meridiem_by_hour(lang: str, hour_noun: str) -> pynini.Fst:
    """
    ``meridiem: "AM"/"PM" hours: "<word>"`` -> the day-part word for that hour, the hour
    and the hour noun, from ``time/meridiem.tsv`` (hour, AM word, PM word) joined with
    ``time/hours.tsv``.

    Malayalam, Kannada and Hindi have no fixed AM/PM words: 10:30 AM is "morning" and
    10:30 PM is "night", so the word is resolved here by the hour.
    """
    from indic_text_normalization.core.utils import data_path, load_labels

    hours = {row[0]: row[1] for row in load_labels(data_path(lang, "time/hours.tsv"), min_fields=2)}
    graphs = []
    for hour, am, pm in load_labels(data_path(lang, "time/meridiem.tsv"), min_fields=3):
        word = hours[hour]
        for marker, day_part in (("AM", am), ("PM", pm)):
            graphs.append(
                pynini.cross(
                    f'meridiem: "{marker}" hours: "{word}"', f"{day_part} {word} {hour_noun}"
                )
            )
    return pynini.union(*graphs).optimize()


class InvariantMeasureFst(GraphFst):
    """
    Measure verbalizer for a language whose unit nouns do not inflect for number, e.g.
        measure { amount: "അഞ്ച്" units: "കിലോഗ്രാം" } -> അഞ്ച് കിലോഗ്രാം
        measure { amount: "ഒന്ന്" units: "കിലോഗ്രാം" } -> ഒരു കിലോഗ്രാം

    Attributes
    ----------
    minus_word : ``str``
        Spoken form of a leading minus sign.
    amount : ``pynini.Fst``
        Rewrite of the spoken amount (the counting one, a range's sandhi); identity if none.
    suffix_field : ``pynini.Fst``
        Consumes an optional ``suffix`` field, emitting the marked suffix for ``sandhi``.
    sandhi : ``pynini.Fst``
        Joins the last noun and the marked suffix.
    """

    def __init__(
        self,
        *,
        minus_word: str,
        amount: pynini.Fst,
        suffix_field: pynini.Fst,
        sandhi: pynini.Fst,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="measure", kind="verbalize", deterministic=deterministic)

        optional_sign = pynini.closure(
            pynini.cross('negative: "true"', f"{minus_word} ") + delete_space, 0, 1
        )
        amount_field = pynutil.delete('amount: "') + amount + pynutil.delete('"')
        units = pynutil.delete('units: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        graph = optional_sign + amount_field + delete_space + insert_space + units
        graph = (graph + suffix_field + delete_preserve_order) @ _NBSP_TO_SPACE
        self.fst = self.delete_tokens(graph @ sandhi).optimize()


class InvariantMoneyFst(GraphFst):
    """
    Money verbalizer for a language whose currency nouns do not inflect for number, e.g.
        money { integer_part: "അൻപത്" currency_maj: "രൂപ" } -> അൻപത് രൂപ
        money { integer_part: "അൻപത്" currency_maj: "രൂപ" fractional_part: "അൻപത്" currency_min: "centiles" } -> അൻപത് രൂപ അൻപത് പൈസ
        money { currency_maj: "രൂപ" integer_part: "പൂജ്യം" fractional_part: "അൻപത്" currency_min: "centiles" } -> അൻപത് പൈസ

    Attributes
    ----------
    lang : ``str``
        Language whose ``money/currency_forms.tsv`` and ``money/major_minor_currencies.tsv``
        name the words.
    minus_word : ``str``
        Spoken form of a leading minus sign.
    amount : ``pynini.Fst``
        Rewrite of the spoken amount (the counting one, a scale phrase's sandhi).
    zero_word : ``str``
        The spoken zero, which a minor-only amount drops (₹0.50 -> അൻപത് പൈസ).
    suffix_field : ``pynini.Fst``
        Consumes an optional ``suffix`` field, emitting the marked suffix for ``sandhi``.
    sandhi : ``pynini.Fst``
        Joins the last noun and the marked suffix.
    """

    def __init__(
        self,
        *,
        lang: str,
        minus_word: str,
        amount: pynini.Fst,
        zero_word: str,
        suffix_field: pynini.Fst,
        sandhi: pynini.Fst,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="money", kind="verbalize", deterministic=deterministic)
        from indic_text_normalization.core.utils import data_path, load_labels

        majors = {
            row[0] for row in load_labels(data_path(lang, "money/currency_forms.tsv"), min_fields=1)
        }
        major_minor = {
            row[0]: row[1]
            for row in load_labels(
                data_path(lang, "money/major_minor_currencies.tsv"), min_fields=2
            )
        }
        integer = pynutil.delete('integer_part: "') + amount + pynutil.delete('"')
        zero_integer = pynutil.delete(f'integer_part: "{zero_word}"')
        minor_field = pynutil.delete('currency_min: "centiles"')

        graphs = []
        for major, minor in major_minor.items():
            if major not in majors:
                continue
            currency = (
                pynutil.delete('currency_maj: "') + pynutil.delete(major) + pynutil.delete('"')
            )
            fraction = (
                pynutil.delete('fractional_part: "')
                + amount
                + pynutil.delete('"')
                + SPACE
                + minor_field
                + pynutil.insert(minor)
                + suffix_field
            )
            graphs.append(integer + SPACE + currency + pynutil.insert(major) + suffix_field)
            graphs.append(integer + SPACE + currency + pynutil.insert(major) + SPACE + fraction)
            graphs.append(
                pynutil.add_weight(
                    zero_integer
                    + pynutil.delete(SPACE)
                    + currency
                    + pynutil.delete(SPACE)
                    + fraction,
                    -0.1,
                )
            )
        optional_sign = pynini.closure(pynini.cross('negative: "true" ', f"{minus_word} "), 0, 1)
        graph = (optional_sign + pynini.union(*graphs)) @ sandhi
        self.fst = self.delete_tokens(graph).optimize()


class InvariantTimeFst(GraphFst):
    """
    Time verbalizer for a language whose clock nouns do not inflect for number, e.g.
        time { hours: "പത്ത്" minutes: "മുപ്പത്" } -> പത്ത് മണി മുപ്പത് മിനിറ്റ്
        time { hours: "പത്ത്" suffix: "ന്" } -> പത്ത് മണിക്ക്
        time { hours: "പത്ത്" minutes: "മുപ്പത്" meridiem: "AM" } -> രാവിലെ പത്ത് മണി മുപ്പത് മിനിറ്റ്

    Attributes
    ----------
    lang : ``str``
        Language whose ``time/meridiem.tsv`` resolves a written AM/PM.
    nouns : ``tuple[str, str, str]``
        Hour, minute and second nouns.
    count : ``pynini.Fst``
        Rewrite of a minute or second count (the counting one); identity if none.
    suffix_field : ``pynini.Fst``
        Consumes an optional ``suffix`` field, emitting the marked suffix for ``sandhi``.
    sandhi : ``pynini.Fst``
        Joins the last noun and the marked suffix.
    """

    def __init__(
        self,
        *,
        lang: str,
        nouns: tuple[str, str, str],
        count: pynini.Fst,
        suffix_field: pynini.Fst,
        sandhi: pynini.Fst,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="time", kind="verbalize", deterministic=deterministic)

        hour_noun, minute_noun, second_noun = nouns

        def field(name: str, value: pynini.Fst, noun: str) -> pynini.Fst:
            return (
                pynutil.delete(f'{name}: "')
                + value
                + pynutil.delete('"')
                + pynutil.insert(f" {noun}")
            )

        any_word = pynini.closure(NOT_QUOTE, 1)
        hours = field("hours", any_word, hour_noun)
        # A written day-part word travels as the meridiem; AM/PM resolve by the hour.
        day_part = (
            pynutil.delete('meridiem: "')
            + pynini.difference(any_word, pynini.union("AM", "PM"))
            + pynutil.delete('"')
            + delete_space
            + insert_space
        )
        head = pynini.union(
            pynini.closure(day_part, 0, 1) + hours, meridiem_by_hour(lang, hour_noun)
        )
        minutes = field("minutes", count, minute_noun)
        seconds = field("seconds", count, second_noun)
        graph = (
            head
            + pynini.closure(delete_space + insert_space + minutes, 0, 1)
            + pynini.closure(delete_space + insert_space + seconds, 0, 1)
            + suffix_field
        )
        self.fst = self.delete_tokens(graph @ sandhi).optimize()


class QuantityDecimalFst(GraphFst):
    """
    Decimal verbalizer with a language hook for a whole number before a scale word, e.g.
        decimal { integer_part: "പന്ത്രണ്ട്" fractional_part: "അഞ്ച്" } -> പന്ത്രണ്ട് ദശാംശം അഞ്ച്
        decimal { integer_part: "ഒന്ന്" quantity: "ലക്ഷം" } -> ഒരു ലക്ഷം
        decimal { integer_part: "അഞ്ച്" quantity: "ആയിരം" } -> അഞ്ചായിരം

    Attributes
    ----------
    minus_word : ``str``
        Spoken form of a leading minus sign.
    point_word : ``str``
        Spoken decimal point.
    whole_quantity : ``pynini.Fst``
        Rewrite of "<whole number> <scale word>" (the counting one, a fused thousand);
        identity if none.
    """

    def __init__(
        self,
        *,
        minus_word: str,
        point_word: str,
        whole_quantity: pynini.Fst,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="decimal", kind="verbalize", deterministic=deterministic)

        delete_one_space = pynutil.delete(" ")
        optional_sign = pynini.closure(
            pynini.cross('negative: "true"', f" {minus_word} ") + delete_one_space, 0, 1
        )
        integer = (
            pynutil.delete('integer_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        fractional = (
            pynutil.insert(f" {point_word} ")
            + pynutil.delete('fractional_part: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )
        quantity = (
            delete_one_space
            + insert_space
            + pynutil.delete('quantity: "')
            + pynini.closure(NOT_QUOTE, 1)
            + pynutil.delete('"')
        )
        graph = optional_sign + (
            (integer + quantity) @ whole_quantity
            | integer + delete_one_space + fractional + pynini.closure(quantity, 0, 1)
        )
        self.fst = self.delete_tokens(graph).optimize()
