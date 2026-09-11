"""
ITN verbalizers, shared by every language: the written form is digits and symbols, so
only a few nouns differ between languages.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    CHAR,
    DIGIT,
    NOT_QUOTE,
    SIGMA,
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


def _optional_field(name: str) -> pynini.Fst:
    """
    Consume an optional space-led ``name: "value"``, emitting the value.
    """
    return pynini.closure(delete_space + _field(name), 0, 1)


def _optional_sign(*, positive: bool) -> pynini.Fst:
    """
    Emit ``-`` for a negative field and, when ``positive``, ``+`` for a positive one.
    """
    sign = pynini.cross('negative: "true"', "-")
    if positive:
        sign |= pynini.cross('positive: "true"', "+")
    return pynini.closure(sign + delete_space, 0, 1)


def _glued_suffix(forms: dict[str, str]) -> pynini.Fst:
    """
    Consume an optional ``suffix: "<written>"``, emitting the form glued to a noun.
    """
    return pynini.closure(
        delete_space
        + pynutil.delete('suffix: "')
        + pynini.string_map(list(forms.items()))
        + pynutil.delete('"'),
        0,
        1,
    )


def _two_digits() -> pynini.Fst:
    """
    Pad a one- or two-digit value to two digits.
    """
    return pynini.union(DIGIT + DIGIT, pynutil.insert("0") + DIGIT).optimize()


class CardinalFst(GraphFst):
    """
    Finite state transducer for verbalizing cardinals, e.g.
        cardinal { negative: "true" integer: "120" } -> -120
        cardinal { positive: "true" integer: "5" } -> +5
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="cardinal", kind="verbalize", deterministic=deterministic)

        self.graph = _optional_sign(positive=True) + _field("integer")
        self.fst = self.delete_tokens(self.graph).optimize()


class DecimalFst(GraphFst):
    """
    Finite state transducer for verbalizing decimals, e.g.
        decimal { integer_part: "12" fractional_part: "5" } -> 12.5
        decimal { integer_part: "5" fractional_part: "5" quantity: "லட்சம்" } -> 5.5 லட்சம்
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="verbalize", deterministic=deterministic)

        self.graph = (
            _optional_sign(positive=True)
            + _field("integer_part")
            + delete_space
            + pynutil.insert(".")
            + _field("fractional_part")
            + pynini.closure(delete_space + insert_space + _field("quantity"), 0, 1)
        )
        self.fst = self.delete_tokens(self.graph).optimize()


class FractionFst(GraphFst):
    """
    Finite state transducer for verbalizing fractions, e.g.
        fraction { numerator: "3" denominator: "4" } -> 3/4
        fraction { integer_part: "2" numerator: "3" denominator: "4" } -> 2 3/4
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="fraction", kind="verbalize", deterministic=deterministic)

        self.graph = (
            pynini.closure(_field("integer_part") + delete_space + insert_space, 0, 1)
            + _field("numerator")
            + delete_space
            + pynutil.insert("/")
            + _field("denominator")
        )
        self.fst = self.delete_tokens(self.graph).optimize()


class OrdinalFst(GraphFst):
    """
    Finite state transducer for verbalizing ordinals, e.g.
        ordinal { integer: "5" morphosyntactic_features: "வது" } -> 5வது
        ordinal { integer: "5వ" } -> 5వ
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="ordinal", kind="verbalize", deterministic=deterministic)

        self.graph = (
            _field("integer") + _optional_field("morphosyntactic_features") + delete_preserve_order
        )
        self.fst = self.delete_tokens(self.graph).optimize()


class MoneyFst(GraphFst):
    """
    Finite state transducer for verbalizing money, e.g.
        money { currency: "₹" integer_part: "50" fractional_part: "50" } -> ₹50.50
        money { currency: "₹" integer_part: "50" suffix: "కి" } -> ₹50కి
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="money", kind="verbalize", deterministic=deterministic)

        # A single spoken minor digit is tens of paise: ஐந்து பைசா is ₹0.05, not ₹0.5.
        fraction = pynutil.delete('fractional_part: "') + _two_digits() + pynutil.delete('"')
        self.graph = (
            _optional_sign(positive=False)
            + _field("currency")
            + delete_space
            + _field("integer_part")
            + pynini.closure(delete_space + pynutil.insert(".") + fraction, 0, 1)
            + _optional_field("suffix")
            + delete_preserve_order
        )
        self.fst = self.delete_tokens(self.graph).optimize()


class DateFst(GraphFst):
    """
    Finite state transducer for verbalizing dates, e.g.
        date { day: "15" month: "ஜூன்" year: "2024" } -> 15 ஜூன் 2024
        date { year: "2024" month: "జూన్" day: "15" } -> 2024 జూన్ 15
        date { month: "ജനുവരി" day: "1" } -> ജനുവരി 1
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="date", kind="verbalize", deterministic=deterministic)

        day, month, year = _field("day"), _field("month"), _field("year")
        sep = delete_space + insert_space
        graph = (
            day + sep + month + pynini.closure(sep + year, 0, 1)
            | month + sep + year
            | year + sep + month + sep + day
            | month + sep + day + pynini.closure(sep + year, 0, 1)
        )
        self.graph = graph + delete_preserve_order
        self.fst = self.delete_tokens(self.graph).optimize()


class TelephoneFst(GraphFst):
    """
    Finite state transducer for verbalizing telephone numbers, e.g.
        telephone { number_part: "9943206870" } -> 9943206870
        telephone { country_code: "+91" number_part: "9876543210" } -> +91 9876543210
        telephone { country_code: "+91" } -> +91
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="verbalize", deterministic=deterministic)

        country_code = _field("country_code")
        self.graph = (
            pynini.closure(country_code + delete_space + insert_space, 0, 1) + _field("number_part")
        ) | country_code
        self.fst = self.delete_tokens(self.graph).optimize()


class TimeFst(GraphFst):
    """
    Finite state transducer for verbalizing times, e.g.
        time { hours: "10" minutes: "30" } -> 10:30
        time { hours: "10" suffix: "కు" } -> 10:00కు
        time { day_part: "காலை" hours: "10" } -> காலை 10:00

    Attributes
    ----------
    duration_nouns : ``tuple[str, str] | None``, optional (default = None)
        Hour and minute nouns to restore after an hour above 23, which is a duration and
        not a clock time (ఇరవై ఐదు గంటలకు -> 25 గంటలకు). None rejects such a token, for a
        tagger that range-binds the hour itself.
    duration_suffixes : ``dict[str, tuple[str, str]] | None``, optional (default = None)
        For a language whose suffix changes shape on a noun: the written suffix and the
        form it takes glued to the hour noun and to the minute noun (Malayalam ന് ->
        ക്ക് on മണി, ിന് on മിനിറ്റ്). None glues the written suffix as it is.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        *,
        duration_nouns: tuple[str, str] | None = None,
        duration_suffixes: dict[str, tuple[str, str]] | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="time", kind="verbalize", deterministic=deterministic)

        valid_hour = pynini.union(
            DIGIT, "1" + DIGIT, "2" + pynini.union("0", "1", "2", "3")
        ).optimize()
        hours = pynutil.delete('hours: "') + valid_hour + pynutil.delete('"')
        minutes = pynutil.delete('minutes: "') + _two_digits() + pynutil.delete('"')
        seconds = pynutil.delete('seconds: "') + _two_digits() + pynutil.delete('"')
        day_part = pynini.closure(_field("day_part") + delete_space + insert_space, 0, 1)

        graph_h = hours + pynutil.insert(":00")
        graph_hm = hours + delete_space + pynutil.insert(":") + minutes
        graph_hms = graph_hm + delete_space + pynutil.insert(":") + seconds
        graph_hs = hours + pynutil.insert(":00:") + delete_space + seconds
        graph = (graph_hms | graph_hm | graph_hs | graph_h) + _optional_field("suffix")

        if duration_nouns is not None:
            hour_noun, minute_noun = duration_nouns
            invalid_hour = pynini.difference(pynini.closure(DIGIT, 1), valid_hour)
            bad_hours = (
                pynutil.delete('hours: "')
                + invalid_hour
                + pynutil.delete('"')
                + pynutil.insert(f" {hour_noun}")
            )
            bad_minutes = (
                pynutil.delete('minutes: "')
                + pynini.closure(DIGIT, 1)
                + pynutil.delete('"')
                + pynutil.insert(f" {minute_noun}")
            )
            hour_suffix = minute_suffix = _optional_field("suffix")
            if duration_suffixes:
                hour_suffix = _glued_suffix({k: v[0] for k, v in duration_suffixes.items()})
                minute_suffix = _glued_suffix({k: v[1] for k, v in duration_suffixes.items()})
            graph |= bad_hours + pynini.union(
                hour_suffix, delete_space + insert_space + bad_minutes + minute_suffix
            )

        self.graph = day_part + graph + delete_preserve_order
        self.fst = self.delete_tokens(self.graph).optimize()


class WordFst(GraphFst):
    """
    Finite state transducer passing plain words through, e.g.
        tokens { name: "வணக்கம்" } -> வணக்கம்
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="word", kind="verbalize", deterministic=deterministic)

        # A value may itself be a U+0022 QUOTATION MARK token, so only the space is excluded.
        chars = pynini.closure(pynini.difference(CHAR, " "), 1)
        graph = pynutil.delete('name: "') + chars + pynutil.delete('"')
        # Multi-word values travel with U+00A0 NO-BREAK SPACE; write them with plain spaces.
        graph = graph @ _NBSP_TO_SPACE
        self.fst = (delete_space + graph + delete_space).optimize()
