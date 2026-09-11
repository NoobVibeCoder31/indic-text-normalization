"""
Kannada TN cardinal tagger.

Tens and units fuse (ಇಪ್ಪತ್ತಮೂರು, ಇಪ್ಪತ್ತೊಂದು); every other group is spaced, the scale word
taking its linking form before a remainder (ನೂರಾ ಐದು, ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತನಾಲ್ಕು, ಒಂದು ಲಕ್ಷದ
ಐವತ್ತು ಸಾವಿರ, ಒಂದು ಕೋಟಿ ಐವತ್ತು ಲಕ್ಷ).
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA, insert_space, unweighted
from indic_text_normalization.core.tn_taggers import cardinal_base
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.utils import data_path
from indic_text_normalization.kn.constants import CASE_SUFFIXES, LANG, ORDINAL_MARKERS, PROFILE
from indic_text_normalization.kn.morphology import ordinal_stem, suffix_sandhi, written_suffix

ZERO_CHAR = PROFILE.digits.zero  # U+0CE6 KANNADA DIGIT ZERO
ONE_CHAR = chr(ord(ZERO_CHAR) + 1)  # U+0CE7 KANNADA DIGIT ONE
NATIVE_DIGIT = PROFILE.digits.digit
NATIVE_NON_ZERO = PROFILE.digits.non_zero
any_digit = PROFILE.any_digit
delete_commas = cardinal_base.delete_commas(any_digit)
indian_comma_pattern = cardinal_base.indian_comma_pattern(any_digit)
intl_comma_pattern = cardinal_base.intl_comma_pattern(any_digit)


def attach_case_suffix(graph: pynini.Fst) -> pynini.Fst:
    """
    Accept a written case suffix after ``graph`` and attach it to the last spoken word with
    sandhi (2024ರಲ್ಲಿ -> ...ನಾಲ್ಕರಲ್ಲಿ, 1000ಕ್ಕೆ -> ಸಾವಿರಕ್ಕೆ, 100000ರ -> ಒಂದು ಲಕ್ಷದ). Kannada
    suffixes have one spelling each, so the written set is the set ITN writes.
    """
    return ((graph + written_suffix()) @ suffix_sandhi()).optimize()


def ordinal_graph(graph: pynini.Fst) -> pynini.Fst:
    """
    Read ``graph`` followed by a written ordinal marker (5ನೇ -> ಐದನೇ, 10ನೆಯ -> ಹತ್ತನೆಯ).
    """
    return ((graph @ ordinal_stem()) + pynini.union(*ORDINAL_MARKERS)).optimize()


class CardinalFst(CardinalBase):
    """
    Finite state transducer for classifying Kannada cardinals, e.g.
        23 -> cardinal { integer: "ಇಪ್ಪತ್ತಮೂರು" }
        2024 -> cardinal { integer: "ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತನಾಲ್ಕು" }
        -೨೩ -> cardinal { negative: "true" integer: "ಇಪ್ಪತ್ತಮೂರು" }
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(PROFILE, deterministic=deterministic)

        digit = pynini.string_file(data_path(LANG, "numbers/digit.tsv")).optimize()
        zero = pynini.string_file(data_path(LANG, "numbers/zero.tsv")).optimize()
        teens_ties = pynini.string_file(data_path(LANG, "numbers/teens_and_ties.tsv")).optimize()
        hundred = pynini.string_file(data_path(LANG, "numbers/hundred.tsv")).optimize()
        hundreds_exact = pynini.string_file(
            data_path(LANG, "numbers/hundreds_exact.tsv")
        ).optimize()
        hundreds_linking = pynini.string_file(
            data_path(LANG, "numbers/hundreds_linking.tsv")
        ).optimize()

        self.digit = digit
        self.zero = zero
        self.teens_and_ties = teens_ties

        zero_delete = pynutil.delete(ZERO_CHAR)
        below_hundred_2 = pynini.union(zero_delete + digit, teens_ties).optimize()
        # ITN also hears the oblique linking form (ನೂರ ಐದು, ಇನ್ನೂರ ಐದು).
        hundreds_linking_alt = hundreds_linking @ (SIGMA + pynutil.delete("ಾ"))

        def hundreds(linking: pynini.Fst) -> pynini.Fst:
            return pynini.union(
                hundred, hundreds_exact, linking + insert_space + below_hundred_2
            ).optimize()

        self.graph_hundreds = hundreds(hundreds_linking)

        def scale_head(multiplier: pynini.Fst, word: str, one_prefix: str | None) -> pynini.Fst:
            """<multiplier> <word>; a multiplier of one is ಒಂದು, bare, or both."""
            many = pynini.difference(multiplier, pynini.accep(ONE_CHAR)) @ pynini.union(
                digit, teens_ties
            )
            head = many + pynutil.insert(f" {word}")
            # The one-path must have the multiplier's own width, or a two-digit group
            # would also accept a single ೧ and swallow a digit of the next group.
            if one_prefix is None:
                one = pynini.cross(ONE_CHAR, f"ಒಂದು {word}") | pynini.cross(ONE_CHAR, word)
            else:
                one = pynini.cross(ONE_CHAR, f"{one_prefix}{word}")
            head |= pynini.compose(multiplier, one)
            return head.optimize()

        def with_remainder(
            head: pynini.Fst, linking: pynini.Fst, remainder: pynini.Fst, n_zeros: int
        ) -> pynini.Fst:
            exact = head + zero_delete**n_zeros
            return pynini.union(exact, (head @ linking) + insert_space + remainder).optimize()

        thousand_link = SIGMA + pynini.cross("ಸಾವಿರ", "ಸಾವಿರದ")
        lakh_link = SIGMA + pynini.cross("ಲಕ್ಷ", "ಲಕ್ಷದ")
        crore_link = SIGMA

        def number_graph(
            hundreds_link: pynini.Fst, thousand_one: str | None, big_one: str | None
        ) -> pynini.Fst:
            graph_hundreds = hundreds(hundreds_link)
            below_thousand_3 = pynini.union(
                zero_delete + below_hundred_2, graph_hundreds
            ).optimize()
            thousands_1 = scale_head(NATIVE_NON_ZERO, "ಸಾವಿರ", thousand_one)
            thousands_2 = scale_head(NATIVE_NON_ZERO + NATIVE_DIGIT, "ಸಾವಿರ", thousand_one)
            graph_thousands = with_remainder(thousands_1, thousand_link, below_thousand_3, 3)
            graph_ten_thousands = with_remainder(thousands_2, thousand_link, below_thousand_3, 3)
            below_lakh_5 = pynini.union(
                zero_delete**2 + below_thousand_3,
                zero_delete + graph_thousands,
                graph_ten_thousands,
            ).optimize()
            lakhs_1 = scale_head(NATIVE_NON_ZERO, "ಲಕ್ಷ", big_one)
            lakhs_2 = scale_head(NATIVE_NON_ZERO + NATIVE_DIGIT, "ಲಕ್ಷ", big_one)
            graph_lakhs = with_remainder(lakhs_1, lakh_link, below_lakh_5, 5)
            graph_ten_lakhs = with_remainder(lakhs_2, lakh_link, below_lakh_5, 5)
            below_crore_7 = pynini.union(
                zero_delete**2 + below_lakh_5,
                zero_delete + graph_lakhs,
                graph_ten_lakhs,
            ).optimize()
            crores_1 = scale_head(NATIVE_NON_ZERO, "ಕೋಟಿ", big_one)
            crores_2 = scale_head(NATIVE_NON_ZERO + NATIVE_DIGIT, "ಕೋಟಿ", big_one)
            graph_crores = with_remainder(crores_1, crore_link, below_crore_7, 7)
            graph_ten_crores = with_remainder(crores_2, crore_link, below_crore_7, 7)
            return pynini.union(
                digit,
                zero,
                teens_ties,
                graph_hundreds,
                graph_thousands,
                graph_ten_thousands,
                graph_lakhs,
                graph_ten_lakhs,
                graph_crores,
                graph_ten_crores,
            ).optimize()

        # 1000 is the bare ಸಾವಿರ; one lakh and one crore take ಒಂದು.
        native_graph = number_graph(hundreds_linking, "", "ಒಂದು ")
        # ITN also hears ಒಂದು ಸಾವಿರ and the oblique hundreds; a bare ಲಕ್ಷ or ಕೋಟಿ stays a word.
        native_alternatives = pynini.union(
            number_graph(hundreds_linking, None, "ಒಂದು "),
            number_graph(hundreds_linking_alt, None, "ಒಂದು "),
        ).optimize()

        single_digit = digit | zero
        graph_leading_zero = pynutil.add_weight(zero + insert_space + single_digit, 0.5)
        native_final = pynini.union(native_graph, graph_leading_zero).optimize()

        def either_script(graph: pynini.Fst) -> pynini.Fst:
            return pynini.union(graph, PROFILE.to_native @ graph).optimize()

        def with_commas(graph: pynini.Fst) -> pynini.Fst:
            grouped = pynini.compose(indian_comma_pattern | intl_comma_pattern, delete_commas)
            return pynini.union(
                pynutil.add_weight(grouped @ either_script(graph), -0.1), either_script(graph)
            )

        squeeze = pynini.cdrewrite(pynini.cross(pynini.closure(" ", 2), " "), "", "", SIGMA)
        strip_leading = pynini.cdrewrite(pynutil.delete(pynini.closure(" ", 1)), "[BOS]", "", SIGMA)
        final_graph = (with_commas(native_final) @ squeeze @ strip_leading).optimize()
        self.final_graph = final_graph
        alternatives = (with_commas(native_alternatives) @ squeeze @ strip_leading).optimize()
        self.itn_input_graph = unweighted(pynini.union(final_graph, alternatives))

        digit_word = pynini.union(digit, zero)
        any_digit_word = pynini.union(digit_word, PROFILE.digits.from_ascii @ digit_word)
        digit_by_digit = (
            any_digit_word + pynini.closure(insert_space + any_digit_word, 1)
        ).optimize()
        self.digit_by_digit = digit_by_digit
        commas_digit_by_digit = (
            pynini.compose(indian_comma_pattern | intl_comma_pattern, delete_commas)
            @ digit_by_digit
        ).optimize()

        self.suffixed_graph = attach_case_suffix(final_graph)

        tagged_integer = (
            self.final_graph
            | pynutil.add_weight(self.suffixed_graph, 0.1)
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
        self.known_suffixes = pynini.union(*CASE_SUFFIXES, *ORDINAL_MARKERS).optimize()

    def attach_case_suffix(self, graph: pynini.Fst, include_vowel: bool = True) -> pynini.Fst:
        del include_vowel
        return attach_case_suffix(graph)

    def ordinal_graph(self, graph: pynini.Fst) -> pynini.Fst:
        return ordinal_graph(graph)
