# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
# Copyright 2015 and onwards Google, Inc.
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

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import load_labels
from indic_text_normalization.te.constants import (
    ASCII_TO_TE_DIGIT,
    ASCII_TO_TE_NUMBER,
    CASE_SUFFIXES,
    DIGIT,
    SIGMA,
    TE_CONSONANT,
    TE_DIGIT,
    TE_LETTER,
    TE_NON_ZERO,
    GraphFst,
    insert_space,
)
from indic_text_normalization.te.utils import get_abs_path

# U+0C66 TELUGU DIGIT ZERO and U+0C67 TELUGU DIGIT ONE anchor the scale graphs.
TE_ZERO_CHAR = "౦"
TE_ONE_CHAR = "౧"

# Telugu vowel signs U+0C3E TELUGU VOWEL SIGN AA .. U+0C4C TELUGU VOWEL SIGN AU.
VOWEL_SIGNS = frozenset(chr(i) for i in range(0x0C3E, 0x0C4D))

any_digit = pynini.union(DIGIT, TE_DIGIT)
delete_commas = (
    any_digit + pynini.closure(pynini.closure(pynutil.delete(","), 0, 1) + any_digit)
).optimize()

# Indian comma format pattern (e.g. 12,34,567) and 3-digit international grouping.
comma = pynini.accep(",")
three_digits = any_digit + any_digit + any_digit
indian_comma_pattern = (
    pynini.closure(any_digit, 1, 2)
    + pynini.closure(comma + any_digit + any_digit, 1)
    + pynini.closure(comma + three_digits, 0, 1)
).optimize()
intl_comma_pattern = (
    pynini.closure(any_digit, 1, 3) + pynini.closure(comma + three_digits, 1)
).optimize()

# Inflected tails an ordinal may carry after -వ (5వది, 5వదానికి); -వో is the colloquial -ో form.
ORDINAL_TAILS = [
    "",
    "ది",
    "దో",
    "దే",
    "దైన",
    "దిగా",
    "దానికి",
    "దానికే",
    "దాన్ని",
    "దానిలో",
    "దానితో",
    "దానికంటే",
    "దానినుండి",
    "దానికోసం",
    "దాంతో",
]

# The ordinal stem drops the cardinal's final -ు/-ి, turns -ై into -య్య-, and leaves a
# consonant-final word (వంద) untouched; the written -వ is then kept as the ordinal marker.
ORDINAL_STEM = SIGMA + pynini.union(
    pynutil.delete("ు"),
    pynutil.delete("ి"),
    pynini.cross("ై", "య్య"),
    TE_CONSONANT,
)


def _suffix_groups() -> tuple[list[str], list[str], list[str]]:
    """
    Split the case suffixes into bare-ల-led, other consonant-led and vowel-sign-led groups.
    """
    la_bare: list[str] = []
    plain: list[str] = []
    vowel: list[str] = []
    for suffix in CASE_SUFFIXES:
        if suffix[0] in VOWEL_SIGNS:
            vowel.append(suffix)
        elif suffix.startswith("ల") and (len(suffix) == 1 or suffix[1] not in VOWEL_SIGNS):
            la_bare.append(suffix)
        else:
            plain.append(suffix)
    return la_bare, plain, vowel


NOMINATIVE_SUFFIXES = ("గా", "గానే")
# The plural -లు attaches only to a singular word (1990లు -> తొంభైలు; వేలు stays వేలు).
PLURAL_SUFFIX = "లు"


def attach_case_suffix(graph: pynini.Fst, include_vowel: bool = True) -> pynini.Fst:
    """
    Accept a written case suffix after ``graph`` and attach it to the last spoken word.

    Telugu is agglutinative, so the suffix attaches verbatim (ఐదు + లో -> ఐదులో). A plural
    scale word takes its oblique -ల before a suffix (వేలు + కి -> వేలకి), a suffix opening
    with the bare plural marker ల absorbs the -లు (వేలు + లలో -> వేలలో), and a vowel-sign
    suffix replaces the final -ు/-ి (ఐదు + ే -> ఐదే).
    """
    la_bare, plain, vowel = _suffix_groups()
    oblique = [s for s in plain if s not in NOMINATIVE_SUFFIXES and s != PLURAL_SUFFIX]
    ends_lu = (SIGMA + pynini.accep("లు")).optimize()
    not_lu_final = graph @ pynini.difference(SIGMA, ends_lu)
    lu_to_la = graph @ (SIGMA + pynini.cross("లు", "ల"))
    lu_dropped = graph @ (SIGMA + pynutil.delete("లు"))
    suffixed = not_lu_final + pynini.union(*la_bare, *oblique, PLURAL_SUFFIX)
    suffixed |= graph + pynini.union(*NOMINATIVE_SUFFIXES)
    suffixed |= lu_to_la + pynini.union(*oblique)
    suffixed |= lu_dropped + pynini.union(*la_bare)
    if not include_vowel:
        return suffixed.optimize()
    vowel_stem = graph @ (
        SIGMA
        + pynini.union(
            pynutil.delete("ు"), pynutil.delete("ి"), pynini.cross("ై", "య్య"), TE_CONSONANT
        )
    )
    suffixed |= vowel_stem + pynini.union(*vowel)
    return suffixed.optimize()


def ordinal_graph(graph: pynini.Fst) -> pynini.Fst:
    """
    Read ``graph`` followed by a written ordinal marker -వ (plus an optional inflected tail).
    """
    tails = pynini.union(*[pynini.accep(t) for t in ORDINAL_TAILS])
    stem = graph @ ORDINAL_STEM
    graph_va = stem + pynini.accep("వ") + tails
    # -వో is spoken as the fused -ో ordinal: 5వో -> ఐదో.
    graph_o = stem + pynini.cross("వో", "ో") + tails
    return pynini.union(graph_va, graph_o).optimize()


class CardinalFst(GraphFst):
    """
    Finite state transducer for classifying Telugu cardinals, e.g.
        -౨౩ -> cardinal { negative: "true"  integer: "ఇరవై మూడు" }
        2024 -> cardinal { integer: "రెండు వేల ఇరవై నాలుగు" }

    Args:
        deterministic: if True will provide a single transduction option,
            for False multiple transduction are generated (used for audio-based normalization)
    """

    def __init__(self, deterministic: bool = True):
        super().__init__(name="cardinal", kind="classify", deterministic=deterministic)

        digit = pynini.string_file(get_abs_path("data/numbers/digit.tsv")).optimize()
        zero = pynini.string_file(get_abs_path("data/numbers/zero.tsv")).optimize()
        teens_ties = pynini.string_file(get_abs_path("data/numbers/teens_and_ties.tsv")).optimize()
        teens_and_ties = pynutil.add_weight(teens_ties, -0.1)
        hundred_exact = pynini.string_file(get_abs_path("data/numbers/hundred.tsv")).optimize()
        hundreds_exact = pynini.string_file(
            get_abs_path("data/numbers/hundreds_exact.tsv")
        ).optimize()
        hundreds_oblique = pynini.string_file(
            get_abs_path("data/numbers/hundreds_oblique.tsv")
        ).optimize()
        digit_rows = [r for r in load_labels(get_abs_path("data/numbers/digit.tsv")) if len(r) >= 2]
        digit_2_9 = pynini.string_map(
            [(k, v) for k, v, *_ in digit_rows if k != TE_ONE_CHAR]
        ).optimize()

        self.digit = digit
        self.zero = zero
        self.teens_and_ties = teens_and_ties

        zero_delete = pynutil.add_weight(pynutil.delete(TE_ZERO_CHAR), -0.1)

        def zeros(count: int) -> pynini.Fst:
            return zero_delete ** count if count else pynini.accep("")

        def scale(
            head_exact: pynini.Fst,
            head_oblique: pynini.Fst,
            n_zeros: int,
            subs: list[tuple[int, pynini.Fst]],
        ) -> pynini.Fst:
            """Exact multiple (all trailing zeros) or oblique head plus a remainder."""
            graph = head_exact + zeros(n_zeros)
            for count, sub in subs:
                graph |= head_oblique + zeros(count) + insert_space + sub
            return graph.optimize()

        # 100-999: వంద; 101-199 take the oblique నూట; 200-900 are రెండు వందలు ... with the
        # oblique వందల before a remainder (205 -> రెండు వందల ఐదు).
        one_hundred_oblique = pynutil.delete(TE_ONE_CHAR) + pynutil.insert("నూట")
        graph_hundreds = (
            hundred_exact
            | one_hundred_oblique + pynutil.delete(TE_ZERO_CHAR) + insert_space + digit
            | one_hundred_oblique + insert_space + teens_ties
            | hundreds_exact
            | hundreds_oblique + pynutil.delete(TE_ZERO_CHAR) + insert_space + digit
            | hundreds_oblique + insert_space + teens_ties
        ).optimize()
        self.graph_hundreds = graph_hundreds

        below_thousand = [(2, digit), (1, teens_ties), (0, graph_hundreds)]

        # 1000-9999: వెయ్యి is invariant; 2-9 thousands are వేలు / oblique వేల.
        one_thousand = pynutil.delete(TE_ONE_CHAR) + pynutil.insert("వెయ్యి")
        graph_thousands = scale(one_thousand, one_thousand, 3, below_thousand)
        graph_thousands |= scale(
            digit_2_9 + pynutil.insert(" వేలు"),
            digit_2_9 + pynutil.insert(" వేల"),
            3,
            below_thousand,
        )
        graph_thousands = graph_thousands.optimize()
        self.graph_thousands = graph_thousands

        graph_ten_thousands = scale(
            teens_and_ties + pynutil.insert(" వేలు"),
            teens_and_ties + pynutil.insert(" వేల"),
            3,
            below_thousand,
        )
        self.graph_ten_thousands = graph_ten_thousands

        below_lakh = [
            (4, digit),
            (3, teens_ties),
            (2, graph_hundreds),
            (1, graph_thousands),
            (0, graph_ten_thousands),
        ]
        one_lakh = pynutil.delete(TE_ONE_CHAR) + pynutil.insert("లక్ష")
        graph_lakhs = scale(one_lakh, one_lakh, 5, below_lakh)
        graph_lakhs |= scale(
            digit_2_9 + pynutil.insert(" లక్షలు"),
            digit_2_9 + pynutil.insert(" లక్షల"),
            5,
            below_lakh,
        )
        graph_lakhs = graph_lakhs.optimize()
        self.graph_lakhs = graph_lakhs

        graph_ten_lakhs = scale(
            teens_and_ties + pynutil.insert(" లక్షలు"),
            teens_and_ties + pynutil.insert(" లక్షల"),
            5,
            below_lakh,
        )
        self.graph_ten_lakhs = graph_ten_lakhs

        below_crore = [
            (6, digit),
            (5, teens_ties),
            (4, graph_hundreds),
            (3, graph_thousands),
            (2, graph_ten_thousands),
            (1, graph_lakhs),
            (0, graph_ten_lakhs),
        ]
        one_crore = pynutil.delete(TE_ONE_CHAR) + pynutil.insert("కోటి")
        graph_crores = scale(one_crore, one_crore, 7, below_crore)
        graph_crores |= scale(
            digit_2_9 + pynutil.insert(" కోట్లు"),
            digit_2_9 + pynutil.insert(" కోట్ల"),
            7,
            below_crore,
        )
        graph_crores = graph_crores.optimize()
        self.graph_crores = graph_crores

        graph_ten_crores = scale(
            teens_and_ties + pynutil.insert(" కోట్లు"),
            teens_and_ties + pynutil.insert(" కోట్ల"),
            7,
            below_crore,
        )
        self.graph_ten_crores = graph_ten_crores

        # Years 1100-1999 read as hundreds: 1947 -> పందొమ్మిది వందల నలభై ఏడు.
        year_shape = pynini.accep(TE_ONE_CHAR) + TE_NON_ZERO + TE_DIGIT + TE_DIGIT
        year_hundreds = scale(
            teens_ties + pynutil.insert(" వందలు"),
            teens_ties + pynutil.insert(" వందల"),
            2,
            [(1, digit), (0, teens_ties)],
        )
        self.graph_year_hundreds = pynini.compose(year_shape, year_hundreds).optimize()

        # Handle leading zeros (e.g., 05 -> సున్నా ఐదు)
        single_digit = digit | zero
        graph_leading_zero = pynutil.add_weight(zero + insert_space + single_digit, 0.5)

        telugu_final_graph = (
            digit
            | zero
            | teens_and_ties
            | graph_hundreds
            | graph_thousands
            | graph_ten_thousands
            | graph_lakhs
            | graph_ten_lakhs
            | graph_crores
            | graph_ten_crores
            | graph_leading_zero
        ).optimize()

        # ASCII digits: convert to Telugu, then apply the same graph.
        arabic_final_graph = pynini.compose(
            pynini.closure(DIGIT, 1), ASCII_TO_TE_NUMBER @ telugu_final_graph
        ).optimize()
        either_script = pynini.union(
            telugu_final_graph, ASCII_TO_TE_NUMBER @ telugu_final_graph
        ).optimize()

        # Any 3-digit international grouping (1,000 / 1,000,000) is read in the Indian
        # idiom after dropping the commas: 1,000,000 -> పది లక్షలు.
        intl_as_indian = (
            pynini.compose(intl_comma_pattern, delete_commas) @ either_script
        ).optimize()
        with_commas = (
            pynini.compose(indian_comma_pattern, delete_commas) @ either_script
        ).optimize()

        final_graph = (
            pynutil.add_weight(intl_as_indian, -0.1)
            | pynutil.add_weight(with_commas, -0.1)
            | telugu_final_graph
            | arabic_final_graph
        )

        # Normalize spacing inside the graph itself so inversion for ITN sees exactly
        # the strings TN emits.
        squeeze = pynini.cdrewrite(pynini.cross(pynini.closure(" ", 2), " "), "", "", SIGMA)
        strip_leading = pynini.cdrewrite(pynutil.delete(pynini.closure(" ", 1)), "[BOS]", "", SIGMA)
        final_graph = (final_graph @ squeeze @ strip_leading).optimize()

        self.final_graph = final_graph
        self.itn_input_graph = final_graph

        # Digit-by-digit fallback for shapes the number grammar rejects, e.g.
        # leading-zero runs (007) and digit strings beyond the crore range.
        digit_word = pynini.union(digit, zero)
        any_digit_word = pynini.union(digit_word, ASCII_TO_TE_DIGIT @ digit_word)
        digit_by_digit = (
            any_digit_word + pynini.closure(insert_space + any_digit_word, 1)
        ).optimize()
        self.digit_by_digit = digit_by_digit
        # A comma-grouped run beyond the crore range (1,00,00,00,000) also falls back
        # to digit-by-digit instead of being split at a comma.
        commas_digit_by_digit = (
            pynini.compose(indian_comma_pattern | intl_comma_pattern, delete_commas)
            @ digit_by_digit
        ).optimize()

        # Case-suffixed numbers, e.g. 2024లో -> ...నాలుగులో.
        self.suffixed_graph = attach_case_suffix(final_graph)
        te_word = pynini.closure(TE_LETTER, 1)
        self.suffix_tail = te_word

        tagged_integer = (
            self.final_graph
            | pynutil.add_weight(self.suffixed_graph, 0.1)
            | pynutil.add_weight(digit_by_digit, 20.0)
            | pynutil.add_weight(commas_digit_by_digit, 20.0)
        )

        optional_minus_graph = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" '), 0, 1
        )
        final_graph = (
            optional_minus_graph
            + pynutil.insert('integer: "')
            + tagged_integer
            + pynutil.insert('"')
        )
        final_graph = self.add_tokens(final_graph)
        self.fst = final_graph.optimize()
