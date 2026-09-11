"""
TN tagger for numeric dates, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import CHAR, DIGIT, GraphFst, insert_space
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.utils import data_path


class DateFst(GraphFst):
    """
    Finite state transducer for classifying dates, e.g.
        15-06-2024 -> date { day: "పదిహేను" month: "జూన్" year: "రెండు వేల ఇరవై నాలుగు" }
        2024-01-15 -> date { year: "..." month: "జనవరి" day: "పదిహేను" }
        క్రీ.శ. 2024 -> date { era: "క్రీస్తు శకం" } (then the year as a cardinal)

    Reads ``date/days.tsv``, ``date/months.tsv`` and ``date/year_suffix.tsv`` of the
    cardinal's language, all keyed by two native digits.
    """

    def __init__(self, cardinal: CardinalBase, deterministic: bool = True) -> None:
        super().__init__(name="date", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        lang = profile.lang
        native_digit = profile.digits.digit
        days = pynini.string_file(data_path(lang, "date/days.tsv"))
        months = pynini.string_file(data_path(lang, "date/months.tsv"))
        year_suffix = pynini.string_file(data_path(lang, "date/year_suffix.tsv"))

        # Two-digit day/month in either script; a single digit is zero-padded.
        pad_zero = pynutil.insert(profile.digits.zero)
        two_digit_input = pynini.union(
            native_digit + native_digit,
            pad_zero + native_digit,
            pynini.compose(DIGIT + DIGIT, profile.to_native),
            pad_zero + pynini.compose(DIGIT, profile.digits.from_ascii),
        ).optimize()
        days_graph = pynini.compose(two_digit_input, days).optimize()
        months_graph = pynini.compose(two_digit_input, months).optimize()

        # Four-digit years; a language may read 1100-1999 as hundreds.
        year_core = cardinal.final_graph
        if cardinal.graph_year_hundreds is not None:
            year_core = pynini.union(
                pynutil.add_weight(cardinal.graph_year_hundreds, -0.05), cardinal.final_graph
            ).optimize()
        year_graph = pynini.union(
            pynini.compose(native_digit**4, year_core),
            pynini.compose(DIGIT**4, profile.to_native @ year_core),
        ).optimize()

        delete_separator = pynutil.delete(pynini.union("-", "/", "."))

        # One date uses one separator throughout. That is enforced by filtering the input
        # below rather than by building each ordering once per separator, which would
        # triple the tagger; without it 15-06.2024 and 2024/06-15 also tag as dates.
        not_separator = pynini.difference(CHAR, pynini.union("-", "/", "."))
        one_separator = pynini.union(
            *[
                pynini.closure(not_separator)
                + separator
                + pynini.closure(not_separator)
                + separator
                + pynini.closure(not_separator)
                for separator in ("-", "/", ".")
            ]
        ).optimize()

        day_component = pynutil.insert('day: "') + days_graph + pynutil.insert('"')
        month_component = pynutil.insert('month: "') + months_graph + pynutil.insert('"')
        # 2-digit years are rejected: 15-06-24 is too ambiguous with number ranges.
        # A case suffix on the date lands on the year (2024లో, 2024కి, 2024వ సంవత్సరం).
        year_component = (
            pynutil.insert('year: "')
            + (
                year_graph
                | cardinal.attach_case_suffix(year_graph)
                | cardinal.ordinal_graph(year_graph)
            )
            + pynutil.insert('"')
        )

        graph_dd_mm_yyyy = (
            day_component
            + insert_space
            + delete_separator
            + month_component
            + insert_space
            + delete_separator
            + year_component
        )
        graph_mm_dd_yyyy = (
            month_component
            + insert_space
            + delete_separator
            + day_component
            + insert_space
            + delete_separator
            + year_component
            + pynutil.insert(" preserve_order: true")
        )
        graph_yyyy_mm_dd = (
            year_component
            + insert_space
            + delete_separator
            + month_component
            + insert_space
            + delete_separator
            + day_component
        )

        era_graph = pynutil.insert('era: "') + year_suffix + pynutil.insert('"')

        # Numeric dates require all three components with a 4-digit year; bare
        # MM-DD / MM-YY shapes are dropped so ranges like 10-20 stay cardinals.
        numeric_dates = pynini.compose(
            one_separator,
            pynutil.add_weight(graph_dd_mm_yyyy, -0.001)
            | pynutil.add_weight(graph_yyyy_mm_dd, -0.001)
            | graph_mm_dd_yyyy,
        )
        final_graph = numeric_dates | pynutil.add_weight(era_graph, -0.001)

        self.final_graph = final_graph.optimize()
        self.fst = self.add_tokens(self.final_graph)
