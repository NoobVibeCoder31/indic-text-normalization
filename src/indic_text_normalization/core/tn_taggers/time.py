"""
TN tagger for clock times, shared by every language.
"""

from dataclasses import dataclass, field

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, SPACE, GraphFst, insert_space
from indic_text_normalization.core.profile import LanguageProfile
from indic_text_normalization.core.utils import data_path


@dataclass(frozen=True)
class TimeWords:
    """
    The written clock vocabulary of one language.

    Attributes
    ----------
    hour_nouns : ``tuple[str, ...]``
        Written hour nouns after a time that the verbalizer speaks itself (గంటలు, గం.).
    hour_noun_suffixes : ``tuple[tuple[str, str], ...]``
        Written inflected hour nouns and the bare suffix they carry (గంటలకు -> కు).
    extra_suffixes : ``tuple[str, ...]``
        Suffixes glued to the digits beyond the profile's case suffixes (లోపు).
    day_parts : ``tuple[str, ...]``
        Day-part words that make a dotted time (10.30) a clock time; they travel as the
        ``meridiem`` field.
    day_part_abbreviations : ``dict[str, str]``
        Written abbreviations of day parts and their full word (ఉ. -> ఉదయం).
    am : ``str``
        ``meridiem`` value for a written AM.
    pm : ``str``
        ``meridiem`` value for a written PM.
    """

    hour_nouns: tuple[str, ...]
    hour_noun_suffixes: tuple[tuple[str, str], ...] = ()
    extra_suffixes: tuple[str, ...] = ()
    day_parts: tuple[str, ...] = ()
    day_part_abbreviations: dict[str, str] = field(default_factory=dict)
    am: str = "AM"
    pm: str = "PM"


class TimeFst(GraphFst):
    """
    Finite state transducer for classifying time, e.g.
        12:30:30 -> time { hours: "పన్నెండు" minutes: "ముప్పై" seconds: "ముప్పై" }
        1:40 -> time { hours: "ఒంటి" minutes: "నలభై" }
        10:00కి -> time { hours: "పది" suffix: "కి" }
        10:30 AM -> time { hours: "పది" minutes: "ముప్పై" meridiem: "పూర్వాహ్నం" }

    Reads ``time/hours.tsv``, ``time/minutes.tsv`` and ``time/seconds.tsv`` (native digits
    to words; hours 0-23, minutes and seconds 01-59).
    """

    def __init__(
        self, profile: LanguageProfile, words: TimeWords, deterministic: bool = True
    ) -> None:
        super().__init__(name="time", kind="classify", deterministic=deterministic)

        lang = profile.lang
        native_digit = profile.digits.digit
        native_zero = profile.digits.zero
        native_non_zero = profile.digits.non_zero
        hours_graph = pynini.string_file(data_path(lang, "time/hours.tsv"))
        minutes_graph = pynini.string_file(data_path(lang, "time/minutes.tsv"))
        seconds_graph = pynini.string_file(data_path(lang, "time/seconds.tsv"))

        delete_colon = pynutil.delete(":")

        delete_leading_zero_native = (
            (native_non_zero + native_digit)
            | (pynutil.delete(native_zero) + native_digit)
            | native_digit
        ).optimize()
        delete_leading_zero_ascii = (
            (pynini.difference(DIGIT, "0") + DIGIT) | (pynutil.delete("0") + DIGIT) | DIGIT
        ).optimize()

        hour_input = (
            pynini.compose(delete_leading_zero_native, hours_graph)
            | pynini.compose(delete_leading_zero_ascii, profile.to_native @ hours_graph)
        ).optimize()
        minute_input = (
            pynini.compose(pynini.closure(native_digit, 1), minutes_graph)
            | pynini.compose(pynini.closure(DIGIT, 1), profile.to_native @ minutes_graph)
        ).optimize()
        second_input = (
            pynini.compose(pynini.closure(native_digit, 1), seconds_graph)
            | pynini.compose(pynini.closure(DIGIT, 1), profile.to_native @ seconds_graph)
        ).optimize()

        self.hours = pynutil.insert('hours: "') + hour_input + pynutil.insert('" ')
        self.minutes = pynutil.insert('minutes: "') + minute_input + pynutil.insert('" ')
        self.seconds = pynutil.insert('seconds: "') + second_input + pynutil.insert('" ')

        # The verbalizer inserts the hour noun itself, so a trailing written hour noun (and
        # a bare case suffix on the digits: 3:30కి) is absorbed; a dative/locative on the
        # time travels as a suffix field attached to the last time noun.
        space = pynini.closure(SPACE, 0, 1)
        suffixes = (*profile.case_suffixes, *words.extra_suffixes)
        bare_suffix_field = pynini.accep("")
        if suffixes:
            bare_suffix_field = (
                pynutil.insert('suffix: "') + pynini.union(*suffixes) + pynutil.insert('" ')
            )
        hour_word_tail = space + pynutil.delete(pynini.union(*words.hour_nouns))
        if words.hour_noun_suffixes:
            hour_word_field = (
                pynutil.insert('suffix: "')
                + pynini.string_map(list(words.hour_noun_suffixes))
                + pynutil.insert('" ')
            )
            hour_word_tail |= space + hour_word_field
        # A bare suffix must be glued to the digits; an hour word may follow a space.
        optional_tail = pynini.closure(
            pynini.union(hour_word_tail, bare_suffix_field) if suffixes else hour_word_tail, 0, 1
        ).optimize()

        graph_hms = (
            self.hours
            + delete_colon
            + insert_space
            + self.minutes
            + delete_colon
            + insert_space
            + self.seconds
            + optional_tail
        )
        double_zero = pynini.union("00", native_zero + native_zero)
        delete_zero_seconds = pynini.closure(pynutil.delete(":" + double_zero), 0, 1)
        graph_hm = (
            self.hours
            + delete_colon
            + insert_space
            + self.minutes
            + delete_zero_seconds
            + optional_tail
        )
        delete_zero_minutes = delete_colon + pynutil.delete(double_zero)
        graph_h = self.hours + delete_zero_minutes + delete_zero_seconds + optional_tail
        # 10:00:30 keeps only the seconds.
        graph_h_s = (
            self.hours
            + delete_zero_minutes
            + delete_colon
            + insert_space
            + self.seconds
            + optional_tail
        )

        # Trailing AM/PM becomes a meridiem field the verbalizer fronts.
        meridiem_word = pynini.cross(
            pynini.union("AM", "am", "A.M.", "a.m."), words.am
        ) | pynini.cross(pynini.union("PM", "pm", "P.M.", "p.m."), words.pm)
        required_meridiem = (
            pynutil.delete(pynini.closure(" ", 0, 1))
            + pynutil.insert('meridiem: "')
            + meridiem_word
            + pynutil.insert('" ')
        )
        meridiem = pynini.closure(required_meridiem, 0, 1)

        final_graph = (
            graph_hms
            | pynutil.add_weight(graph_hm, 1.0)
            | pynutil.add_weight(graph_h_s, 1.0)
            | pynutil.add_weight(graph_h, 0.8)
        ) + meridiem

        # A bare hour with AM/PM is a clock time: 7 AM, 7pm.
        final_graph |= pynutil.add_weight(self.hours + required_meridiem, 0.9)

        # Press-style dotted time (10.30) is only a time with a clock context: a trailing
        # hour noun, or a day-part word before or after it.
        two_digit_minutes = pynini.compose(
            pynini.union(native_digit + native_digit, DIGIT + DIGIT), minute_input
        )
        dotted = (
            self.hours
            + pynutil.delete(".")
            + insert_space
            + pynutil.insert('minutes: "')
            + two_digit_minutes
            + pynutil.insert('" ')
        )
        # 6.00 reads as the bare hour.
        dotted |= self.hours + pynutil.delete("." + double_zero)
        # With a day-part word the time may also carry a glued suffix (ఉదయం 10.30కి).
        dotted_tail = pynini.closure(hour_word_tail | bare_suffix_field, 0, 1)
        contexts = [(w, w) for w in words.day_parts] + list(words.day_part_abbreviations.items())
        dotted_graphs = [dotted + hour_word_tail, dotted + dotted_tail + required_meridiem]
        for written, spoken in contexts:
            meridiem_field = pynutil.insert(f'meridiem: "{spoken}" ')
            dotted_graphs.append(
                pynutil.delete(written)
                + pynutil.delete(" ")
                + dotted
                + dotted_tail
                + meridiem_field
            )
            dotted_graphs.append(dotted + space + pynutil.delete(written) + meridiem_field)
        # A cued dotted time must outrank a measure reading of the same span (10.30 గం.).
        final_graph |= pynutil.add_weight(pynini.union(*dotted_graphs), -2.5)

        self.fst = self.add_tokens(final_graph).optimize()
