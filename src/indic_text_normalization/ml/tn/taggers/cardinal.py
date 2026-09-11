"""
Malayalam TN cardinal tagger.

Below a thousand a number is one word: tens and units fuse through the linking form
(ഇരുപത്തി + മൂന്ന് -> ഇരുപത്തിമൂന്ന്) and so does a hundreds remainder (നൂറ്റി + ഇരുപത്തിമൂന്ന്
-> നൂറ്റിയിരുപത്തിമൂന്ന്). Scale groups are spaced, the scale word taking its linking form
before a remainder (രണ്ടായിരത്തി ഇരുപത്തിനാല്, ഒരു ലക്ഷത്തി അൻപതിനായിരം, രണ്ട് കോടി അൻപത് ലക്ഷം).
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA, insert_space, unweighted
from indic_text_normalization.core.tn_taggers import cardinal_base
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.ml.constants import (
    LANG,
    ORDINAL_MARKER_VARIANTS,
    ORDINAL_MARKERS,
    PROFILE,
    WRITTEN_SUFFIXES,
)
from indic_text_normalization.ml.morphology import (
    ONE_AS_ORU,
    canonical_written_suffixes,
    join_after_i,
    linking_form,
    ordinal_stem,
    suffix_sandhi,
    written_suffix_to_spoken,
)

ZERO_CHAR = PROFILE.digits.zero  # U+0D66 MALAYALAM DIGIT ZERO
ONE_CHAR = chr(ord(ZERO_CHAR) + 1)  # U+0D67 MALAYALAM DIGIT ONE
NATIVE_DIGIT = PROFILE.digits.digit
NATIVE_NON_ZERO = PROFILE.digits.non_zero
any_digit = PROFILE.any_digit
delete_commas = cardinal_base.delete_commas(any_digit)
indian_comma_pattern = cardinal_base.indian_comma_pattern(any_digit)
intl_comma_pattern = cardinal_base.intl_comma_pattern(any_digit)

# 1 പേർ is ഒരാൾ, not ഒരു പേർ.
COUNTED_ONE_EXCEPTIONS = {"പേർ": "ഒരാൾ"}


def attach_case_suffix(graph: pynini.Fst, include_vowel: bool = True) -> pynini.Fst:
    """
    Accept a written case suffix after ``graph`` and attach it to the last spoken word with
    sandhi (2024ൽ -> ...നാലിൽ, 1000ൽ -> ആയിരത്തിൽ, 5ഉം -> അഞ്ചും).

    With ``include_vowel`` False only the canonical spelling of each suffix is accepted,
    which is the set ITN writes.
    """
    suffixes = written_suffix_to_spoken() if include_vowel else canonical_written_suffixes()
    return ((graph + suffixes) @ suffix_sandhi()).optimize()


def ordinal_graph(graph: pynini.Fst) -> pynini.Fst:
    """
    Read ``graph`` followed by the written ordinal marker -ാം and an optional tail
    (5-ാം -> അഞ്ചാം, 5ാമത്തെ -> അഞ്ചാമത്തെ, 1000-ാം -> ആയിരാം).
    """
    marker = pynini.union(
        *[pynini.accep(m) for m in ORDINAL_MARKERS],
        *[pynutil.add_weight(pynini.cross(v, m), 0.01) for m, v in ORDINAL_MARKER_VARIANTS.items()],
    )
    return ((graph @ ordinal_stem()) + marker).optimize()


class CardinalFst(CardinalBase):
    """
    Finite state transducer for classifying Malayalam cardinals, e.g.
        23 -> cardinal { integer: "ഇരുപത്തിമൂന്ന്" }
        2024 -> cardinal { integer: "രണ്ടായിരത്തി ഇരുപത്തിനാല്" }
        -൨൩ -> cardinal { negative: "true" integer: "ഇരുപത്തിമൂന്ന്" }
        1 ദിവസം -> cardinal { integer: "ഒരു ദിവസം" }
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
        thousands_exact = pynini.string_file(data_path(LANG, "numbers/thousands.tsv")).optimize()

        self.digit = digit
        self.zero = zero
        self.teens_and_ties = teens_ties

        zero_delete = pynutil.delete(ZERO_CHAR)
        join = join_after_i()
        linking = linking_form()

        # 1-99 in one or two digits, and 1-999 in one to three digits (leading zeros
        # deleted), as they stand at the tail of a longer number.
        below_hundred_2 = pynini.union(zero_delete + digit, teens_ties).optimize()
        graph_hundreds = pynini.union(
            hundred,
            hundreds_exact,
            hundreds_linking + (below_hundred_2 @ join),
        ).optimize()
        self.graph_hundreds = graph_hundreds
        below_thousand_3 = pynini.union(zero_delete + below_hundred_2, graph_hundreds).optimize()

        # ITN also hears a spaced hundreds remainder (നൂറ്റി ഇരുപത്) and a glued scale
        # remainder (രണ്ടായിരത്തിയിരുപത്തിനാല്), so the graph is built once per joining style.
        spaced_hundreds = pynini.union(
            hundred, hundreds_exact, hundreds_linking + insert_space + below_hundred_2
        ).optimize()
        hundreds_by_style = {True: graph_hundreds, False: spaced_hundreds}

        def with_remainder(
            head: pynini.Fst, remainder: pynini.Fst, n_zeros: int, fused: bool
        ) -> pynini.Fst:
            """A scale group as its exact word, or as its linking form before a remainder."""
            exact = head + zero_delete**n_zeros
            joiner = (remainder @ join) if fused else insert_space + remainder
            return pynini.union(exact, (head @ linking) + joiner).optimize()

        # Thousands 1,000-99,999: the fused table word, ആയിരത്തി before a remainder.
        thousands_1 = pynini.compose(NATIVE_NON_ZERO, thousands_exact)
        thousands_2 = pynini.compose(NATIVE_NON_ZERO + NATIVE_DIGIT, thousands_exact)
        self.graph_thousands = with_remainder(thousands_1, below_thousand_3, 3, False)

        def scale_head(multiplier: pynini.Fst, word: str, one_prefix: str) -> pynini.Fst:
            """<multiplier> <word>; a multiplier of one is the counting ഒരു (or bare)."""
            many = pynini.difference(multiplier, pynini.accep(ONE_CHAR)) @ pynini.union(
                digit, teens_ties
            )
            # The one-path must have the multiplier's own width, or a two-digit group
            # would also accept a single ൧ and swallow a digit of the next group.
            one = pynini.compose(multiplier, pynini.cross(ONE_CHAR, one_prefix.rstrip()))
            head = pynini.union(many + pynutil.insert(f" {word}"), one + pynutil.insert(f" {word}"))
            # A bare scale word for one: the output opens with a space to strip.
            return head.optimize()

        def number_graph(one_prefix: str, fuse_hundreds: bool, fuse_scales: bool) -> pynini.Fst:
            graph_hundreds = hundreds_by_style[fuse_hundreds]
            below_thousand_3 = pynini.union(
                zero_delete + below_hundred_2, graph_hundreds
            ).optimize()
            graph_thousands = with_remainder(thousands_1, below_thousand_3, 3, fuse_scales)
            graph_ten_thousands = with_remainder(thousands_2, below_thousand_3, 3, fuse_scales)
            below_lakh_5 = pynini.union(
                zero_delete**2 + below_thousand_3,
                zero_delete + graph_thousands,
                graph_ten_thousands,
            ).optimize()
            lakhs_1 = scale_head(NATIVE_NON_ZERO, "ലക്ഷം", one_prefix)
            lakhs_2 = scale_head(NATIVE_NON_ZERO + NATIVE_DIGIT, "ലക്ഷം", one_prefix)
            graph_lakhs = with_remainder(lakhs_1, below_lakh_5, 5, fuse_scales)
            graph_ten_lakhs = with_remainder(lakhs_2, below_lakh_5, 5, fuse_scales)
            below_crore_7 = pynini.union(
                zero_delete**2 + below_lakh_5,
                zero_delete + graph_lakhs,
                graph_ten_lakhs,
            ).optimize()
            crores_1 = scale_head(NATIVE_NON_ZERO, "കോടി", one_prefix)
            crores_2 = scale_head(NATIVE_NON_ZERO + NATIVE_DIGIT, "കോടി", one_prefix)
            # കോടി has no linking form; the remainder simply follows after a space.
            graph_crores = pynini.union(
                crores_1 + zero_delete**7, crores_1 + insert_space + below_crore_7
            )
            graph_ten_crores = pynini.union(
                crores_2 + zero_delete**7, crores_2 + insert_space + below_crore_7
            )
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

        native_graph = number_graph("ഒരു ", True, False)
        # ITN also hears the other joinings. A bare ലക്ഷം or കോടി stays a word: reading it
        # as a number would swallow the kept scale word of 5.5 ലക്ഷം or ₹5 കോടി.
        native_alternatives = pynini.union(
            *[
                number_graph("ഒരു ", hundreds, scales)
                for hundreds in (True, False)
                for scales in (False, True)
                if (hundreds, scales) != (True, False)
            ]
        ).optimize()

        # Handle leading zeros (e.g., 05 -> പൂജ്യം അഞ്ച്)
        single_digit = digit | zero
        graph_leading_zero = pynutil.add_weight(zero + insert_space + single_digit, 0.5)
        native_final = pynini.union(native_graph, graph_leading_zero).optimize()

        def either_script(graph: pynini.Fst) -> pynini.Fst:
            return pynini.union(graph, PROFILE.to_native @ graph).optimize()

        def with_commas(graph: pynini.Fst) -> pynini.Fst:
            # Any 3-digit international grouping (1,000,000) is read in the Indian idiom.
            grouped = pynini.compose(indian_comma_pattern | intl_comma_pattern, delete_commas)
            return pynini.union(
                pynutil.add_weight(grouped @ either_script(graph), -0.1), either_script(graph)
            )

        final_graph = with_commas(native_final)
        # A bare scale word for one opens with a space when the prefix is empty; squeeze.
        squeeze = pynini.cdrewrite(pynini.cross(pynini.closure(" ", 2), " "), "", "", SIGMA)
        strip_leading = pynini.cdrewrite(pynutil.delete(pynini.closure(" ", 1)), "[BOS]", "", SIGMA)
        final_graph = (final_graph @ squeeze @ strip_leading).optimize()
        self.final_graph = final_graph
        alternatives = (with_commas(native_alternatives) @ squeeze @ strip_leading).optimize()
        # Exported to ITN unweighted, with the spaced and glued joining alternatives.
        self.itn_input_graph = unweighted(pynini.union(final_graph, alternatives))

        # Digit-by-digit fallback for shapes the number grammar rejects (007, 10+ digits).
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

        # Case-suffixed numbers, e.g. 2024ൽ -> ...നാലിൽ.
        self.suffixed_graph = attach_case_suffix(final_graph)

        # A count noun after the number: 1 takes the counting ഒരു (1 ദിവസം -> ഒരു ദിവസം,
        # 1 പേർ -> ഒരാൾ). The tokenizer pre-pass joins the pair with U+00A0 NO-BREAK SPACE.
        nouns = [row[0] for row in load_labels(data_path(LANG, "numbers/count_nouns.tsv"))]
        units = load_labels(data_path(LANG, "measure/unit.tsv"), min_fields=2)
        count_nouns = sorted({*nouns, *[row[1] for row in units]})
        letters = pynini.closure(PROFILE.letter)
        one = pynini.union(ONE_CHAR, "1")
        regular_nouns = pynini.union(*[n for n in count_nouns if n not in COUNTED_ONE_EXCEPTIONS])
        counted = (
            (
                final_graph
                @ pynini.union(ONE_AS_ORU, pynini.difference(SIGMA, pynini.accep("ഒന്ന്")))
            )
            + pynini.cross(" ", " ")
            + regular_nouns
            + letters
        )
        for noun, word in COUNTED_ONE_EXCEPTIONS.items():
            counted |= pynutil.delete(one) + pynini.cross(" " + noun, word) + letters
            counted |= (
                (final_graph @ pynini.difference(SIGMA, pynini.accep("ഒന്ന്")))
                + pynini.cross(" ", " ")
                + noun
                + letters
            )
        self.counted_graph = counted.optimize()

        tagged_integer = (
            self.final_graph
            | self.counted_graph
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
        markers = pynini.union(*ORDINAL_MARKERS, *ORDINAL_MARKER_VARIANTS.values())
        self.known_suffixes = pynini.union(pynini.union(*WRITTEN_SUFFIXES), markers).optimize()

    def attach_case_suffix(self, graph: pynini.Fst, include_vowel: bool = True) -> pynini.Fst:
        return attach_case_suffix(graph, include_vowel)

    def ordinal_graph(self, graph: pynini.Fst) -> pynini.Fst:
        return ordinal_graph(graph)
