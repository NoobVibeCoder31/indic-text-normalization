"""
Hindi TN cardinal tagger.

Numbers below a hundred are lexical (a table of ninety-nine words); every larger group is
spaced (दो हज़ार चौबीस, एक लाख पचास हज़ार, एक करोड़ पचास लाख), and years 1100-1999 may read as
hundreds (उन्नीस सौ सैंतालीस).
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA, insert_space, unweighted
from indic_text_normalization.core.tn_taggers import cardinal_base
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.utils import data_path
from indic_text_normalization.hi.constants import (
    LANG,
    LEXICAL_ORDINAL_WORDS,
    ORDINAL_MARKERS,
    PROFILE,
)

ZERO_CHAR = PROFILE.digits.zero  # U+0966 DEVANAGARI DIGIT ZERO
ONE_CHAR = chr(ord(ZERO_CHAR) + 1)  # U+0967 DEVANAGARI DIGIT ONE
NATIVE_DIGIT = PROFILE.digits.digit
NATIVE_NON_ZERO = PROFILE.digits.non_zero
any_digit = PROFILE.any_digit
delete_commas = cardinal_base.delete_commas(any_digit)
indian_comma_pattern = cardinal_base.indian_comma_pattern(any_digit)
intl_comma_pattern = cardinal_base.intl_comma_pattern(any_digit)

HUNDRED = "सौ"
THOUSAND = "हज़ार"
LAKH = "लाख"
CRORE = "करोड़"


def ordinal_graph(graph: pynini.Fst) -> pynini.Fst:
    """
    Read ``graph`` followed by a written ordinal marker: 5वाँ -> पाँचवाँ, 5वीं -> पाँचवीं,
    5वें -> पाँचवें. The anusvara spellings 5वां/5वे are read as the chandrabindu forms.
    """
    marker = pynini.union(
        *[
            pynini.accep(m) if m == spoken else pynutil.add_weight(pynini.cross(m, spoken), 0.01)
            for m, spoken in ORDINAL_MARKERS.items()
        ]
    )
    return (graph + marker).optimize()


def lexical_ordinals() -> pynini.Fst:
    """
    The first six ordinals, written with their own endings: 1ला -> पहला, 2री -> दूसरी, 6ठे -> छठे.
    """
    to_native = PROFILE.digits.from_ascii
    graphs = []
    for (digit, marker), word in LEXICAL_ORDINAL_WORDS.items():
        native = pynini.shortestpath(digit @ to_native).string()
        graphs.append(pynini.cross(digit + marker, word))
        graphs.append(pynini.cross(native + marker, word))
    return pynini.union(*graphs).optimize()


class CardinalFst(CardinalBase):
    """
    Finite state transducer for classifying Hindi cardinals, e.g.
        23 -> cardinal { integer: "तेईस" }
        2024 -> cardinal { integer: "दो हज़ार चौबीस" }
        -२३ -> cardinal { negative: "true" integer: "तेईस" }
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(PROFILE, deterministic=deterministic)

        digit = pynini.string_file(data_path(LANG, "numbers/digit.tsv")).optimize()
        zero = pynini.string_file(data_path(LANG, "numbers/zero.tsv")).optimize()
        teens_ties = pynini.string_file(data_path(LANG, "numbers/teens_and_ties.tsv")).optimize()

        self.digit = digit
        self.zero = zero
        self.teens_and_ties = teens_ties

        zero_delete = pynutil.delete(ZERO_CHAR)
        below_hundred_2 = pynini.union(zero_delete + digit, teens_ties).optimize()
        below_hundred_1_2 = pynini.union(digit, teens_ties).optimize()

        def scale(
            multiplier: pynini.Fst, word: str, remainder: pynini.Fst, n_zeros: int
        ) -> pynini.Fst:
            """<multiplier> <word>, exact or followed by a spaced remainder."""
            head = multiplier + pynutil.insert(f" {word}")
            exact = head + zero_delete**n_zeros
            return pynini.union(exact, head + insert_space + remainder).optimize()

        # 100-999: N सौ, with the counted एक (एक सौ, एक सौ बीस).
        graph_hundreds = scale(digit, HUNDRED, below_hundred_2, 2)
        self.graph_hundreds = graph_hundreds
        below_thousand_3 = pynini.union(zero_delete + below_hundred_2, graph_hundreds).optimize()

        def number_graph() -> pynini.Fst:
            thousands_1 = scale(digit, THOUSAND, below_thousand_3, 3)
            thousands_2 = scale(teens_ties, THOUSAND, below_thousand_3, 3)
            below_lakh_5 = pynini.union(
                zero_delete**2 + below_thousand_3, zero_delete + thousands_1, thousands_2
            ).optimize()
            lakhs_1 = scale(digit, LAKH, below_lakh_5, 5)
            lakhs_2 = scale(teens_ties, LAKH, below_lakh_5, 5)
            below_crore_7 = pynini.union(
                zero_delete**2 + below_lakh_5, zero_delete + lakhs_1, lakhs_2
            ).optimize()
            crores_1 = scale(digit, CRORE, below_crore_7, 7)
            crores_2 = scale(teens_ties, CRORE, below_crore_7, 7)
            return pynini.union(
                below_hundred_1_2,
                zero,
                graph_hundreds,
                thousands_1,
                thousands_2,
                lakhs_1,
                lakhs_2,
                crores_1,
                crores_2,
            ).optimize()

        native_graph = number_graph()

        # Years 1100-1999 read as hundreds: 1947 -> उन्नीस सौ सैंतालीस, 1900 -> उन्नीस सौ.
        year_shape = pynini.accep(ONE_CHAR) + NATIVE_NON_ZERO + NATIVE_DIGIT + NATIVE_DIGIT
        year_hundreds = scale(teens_ties, HUNDRED, below_hundred_2, 2)
        self.graph_year_hundreds = pynini.union(
            pynini.compose(year_shape, year_hundreds),
            pynini.compose(PROFILE.to_native @ year_shape, year_hundreds),
        ).optimize()

        single_digit = digit | zero
        graph_leading_zero = pynutil.add_weight(zero + insert_space + single_digit, 0.5)
        native_final = pynini.union(native_graph, graph_leading_zero).optimize()

        def either_script(graph: pynini.Fst) -> pynini.Fst:
            return pynini.union(graph, PROFILE.to_native @ graph).optimize()

        grouped = pynini.compose(indian_comma_pattern | intl_comma_pattern, delete_commas)
        final_graph = pynini.union(
            pynutil.add_weight(grouped @ either_script(native_final), -0.1),
            either_script(native_final),
        )
        squeeze = pynini.cdrewrite(pynini.cross(pynini.closure(" ", 2), " "), "", "", SIGMA)
        self.final_graph = (final_graph @ squeeze).optimize()
        self.itn_input_graph = unweighted(self.final_graph)

        digit_word = pynini.union(digit, zero)
        any_digit_word = pynini.union(digit_word, PROFILE.digits.from_ascii @ digit_word)
        digit_by_digit = (
            any_digit_word + pynini.closure(insert_space + any_digit_word, 1)
        ).optimize()
        self.digit_by_digit = digit_by_digit
        commas_digit_by_digit = (grouped @ digit_by_digit).optimize()

        tagged_integer = (
            self.final_graph
            | pynutil.add_weight(digit_by_digit, 20.0)
            | pynutil.add_weight(commas_digit_by_digit, 20.0)
        )
        optional_minus_graph = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" '), 0, 1
        )
        graph = (
            optional_minus_graph
            + pynutil.insert('integer: "')
            + tagged_integer
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()

        self.ordinal_tails = ("",)
        self.known_suffixes = pynini.union(
            *ORDINAL_MARKERS, *[m for _, m in LEXICAL_ORDINAL_WORDS]
        ).optimize()

    def attach_case_suffix(self, graph: pynini.Fst, include_vowel: bool = True) -> pynini.Fst:
        # Hindi writes its postpositions as separate words: nothing glues to a digit.
        del graph, include_vowel
        return pynini.Fst()

    def ordinal_graph(self, graph: pynini.Fst) -> pynini.Fst:
        return ordinal_graph(graph)
