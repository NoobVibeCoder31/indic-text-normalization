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

from indic_text_normalization.ta.constants import (
    CHAR,
    DIGIT,
    SIGMA,
    TA_DIGIT,
    GraphFst,
    insert_space,
)
from indic_text_normalization.ta.utils import get_abs_path

# Convert Arabic digits (0-9) to Tamil digits (௦-௯)
arabic_to_tamil_digit = pynini.string_map(
    [
        ("0", "௦"),
        ("1", "௧"),
        ("2", "௨"),
        ("3", "௩"),
        ("4", "௪"),
        ("5", "௫"),
        ("6", "௬"),
        ("7", "௭"),
        ("8", "௮"),
        ("9", "௯"),
    ]
).optimize()
arabic_to_tamil_number = pynini.closure(arabic_to_tamil_digit).optimize()

# Create a graph that deletes commas from digit sequences
# This handles Indian number format where commas are separators (e.g., 1,000,001 or ௧,௦௦௦,௦௦௧)
any_digit = pynini.union(DIGIT, TA_DIGIT)
delete_commas = (
    any_digit + pynini.closure(pynini.closure(pynutil.delete(","), 0, 1) + any_digit)
).optimize()

# Indian comma format pattern (e.g. 12,34,567)
comma = pynini.accep(",")
three_digits = any_digit + any_digit + any_digit
indian_comma_pattern = (
    pynini.closure(any_digit, 1, 2)
    + pynini.closure(comma + any_digit + any_digit, 1)
    + pynini.closure(comma + three_digits, 0, 1)
).optimize()


class CardinalFst(GraphFst):
    """
    Finite state transducer for classifying Tamil cardinals, e.g.
        -௨௩ -> cardinal { negative: "true"  integer: "இருபத்துமூன்று" }

    Args:
        deterministic: if True will provide a single transduction option,
            for False multiple transduction are generated (used for audio-based normalization)
    """

    def __init__(self, deterministic: bool = True):
        super().__init__(name="cardinal", kind="classify", deterministic=deterministic)

        # Load Tamil number mappings efficiently
        digit = pynini.string_file(get_abs_path("data/numbers/digit.tsv")).optimize()
        zero = pynini.string_file(get_abs_path("data/numbers/zero.tsv")).optimize()
        teens_ties = pynini.string_file(get_abs_path("data/numbers/teens_and_ties.tsv")).optimize()
        teens_and_ties = pynutil.add_weight(teens_ties, -0.1)

        # Load special hundred forms (200-900 combined forms)
        hundreds_combined = pynini.string_file(
            get_abs_path("data/numbers/hundreds_combined.tsv")
        ).optimize()
        hundred_exact = pynini.string_file(get_abs_path("data/numbers/hundred.tsv")).optimize()

        self.digit = digit
        self.zero = zero
        self.teens_and_ties = teens_and_ties

        # Helper function to create graphs with zero padding efficiently
        def create_graph_suffix(
            digit_graph: pynini.Fst, suffix: pynini.Fst, zeros_counts: int
        ) -> pynini.Fst:
            """Create graph with suffix and zero padding"""
            zero_delete = pynutil.add_weight(pynutil.delete("௦"), -0.1)
            if zeros_counts == 0:
                return digit_graph + suffix
            return digit_graph + (zero_delete**zeros_counts) + suffix

        def create_larger_number_graph(
            digit_graph: pynini.Fst,
            suffix: pynini.Fst,
            zeros_counts: int,
            sub_graph: pynini.Fst,
        ) -> pynini.Fst:
            """Create graph for larger numbers with sub-components"""
            zero_delete = pynutil.add_weight(pynutil.delete("௦"), -0.1)
            if zeros_counts == 0:
                return digit_graph + suffix + insert_space + sub_graph
            return digit_graph + suffix + (zero_delete**zeros_counts) + insert_space + sub_graph

        # Special case: exactly 100 = நூறு
        graph_hundred_exact = hundred_exact

        # For 101-109: நூற்று + digit (e.g., 101 = நூற்றொன்று)
        # Pattern: 1 + 0 + digit -> நூற்று + digit
        graph_101_109 = (
            pynutil.delete("௧")
            + pynutil.delete("௦")
            + pynutil.insert(" நூற்று")
            + insert_space
            + digit
        )

        # For 110-199: நூற்று + tens/teens
        # Pattern: 1 + (10-99) -> நூற்று + tens/teens
        # Note: Special cases 150, 160, 170, 180, 190 are handled separately below
        # They will have priority in the union, so this general pattern won't conflict
        graph_110_199_general = (
            pynutil.delete("௧") + pynutil.insert(" நூற்று") + insert_space + teens_ties
        )

        # Special cases for 150, 160, 170, 180, 190: combined forms
        # 150 = நூற்றைம்பது, 160 = நூற்றறுபது, 170 = நூற்றெழுபது, 180 = நூற்றெண்பது, 190 = நூற்றொண்ணூறு
        graph_150 = pynini.cross("௧௫௦", "நூற்றைம்பது")
        graph_160 = pynini.cross("௧௬௦", "நூற்றறுபது")
        graph_170 = pynini.cross("௧௭௦", "நூற்றெழுபது")
        graph_180 = pynini.cross("௧௮௦", "நூற்றெண்பது")
        graph_150_190 = graph_150 | graph_160 | graph_170 | graph_180

        # For 151-159, 161-169, etc.: special combined forms + digit
        # 151 = நூற்றைம்பத்தொன்று, etc.
        graph_151_159 = (
            pynutil.delete("௧")
            + pynutil.delete("௫")
            + pynutil.insert("நூற்றைம்பத்து")
            + insert_space
            + digit
        )
        graph_161_169 = (
            pynutil.delete("௧")
            + pynutil.delete("௬")
            + pynutil.insert("நூற்றறுபத்து")
            + insert_space
            + digit
        )
        graph_171_179 = (
            pynutil.delete("௧")
            + pynutil.delete("௭")
            + pynutil.insert("நூற்றெழுபத்து")
            + insert_space
            + digit
        )
        graph_181_189 = (
            pynutil.delete("௧")
            + pynutil.delete("௮")
            + pynutil.insert("நூற்றெண்பத்து")
            + insert_space
            + digit
        )
        graph_151_199_special = graph_151_159 | graph_161_169 | graph_171_179 | graph_181_189

        # Combine all 100-199 patterns
        # Order matters: special cases first (they're more specific)
        graph_100_199 = (
            graph_hundred_exact
            | graph_101_109
            | graph_150_190  # Special cases first
            | graph_151_199_special  # Special cases first
            | graph_110_199_general  # General pattern last
        )

        # Exact hundreds 200-900 come from the joined-form table (இருநூறு ... தொள்ளாயிரம்).
        tamil_zero = "௦"
        graph_hundreds_exact = pynini.string_file(
            get_abs_path("data/numbers/hundreds_exact.tsv")
        ).optimize()

        # For 201-209: joined stem + digit (e.g., 205 = இருநூற்று ஐந்து)
        graph_201_209_2_8 = hundreds_combined + pynutil.delete(tamil_zero) + insert_space + digit

        # Special case: 901-909: தொள்ளாயிரத்து + digit
        graph_901_909 = (
            pynutil.delete("௯")
            + pynutil.delete(tamil_zero)
            + pynutil.insert("தொள்ளாயிரத்து")
            + insert_space
            + digit
        )
        graph_201_209 = graph_201_209_2_8 | graph_901_909

        # For 210-899: joined stem + tens/teens (e.g., 456 = நானூற்று ஐம்பத்தாறு)
        graph_210_899 = hundreds_combined + insert_space + teens_ties

        # Special case: 910-999: தொள்ளாயிரத்து + tens/teens
        graph_910_999 = (
            pynutil.delete("௯") + pynutil.insert(" தொள்ளாயிரத்து") + insert_space + teens_ties
        )
        graph_210_999 = graph_210_899 | graph_910_999

        # Combine all hundred patterns
        graph_all_hundreds = (
            graph_100_199 | graph_hundreds_exact | graph_201_209 | graph_210_999
        ).optimize()

        self.graph_hundreds = graph_all_hundreds

        # Thousands and Ten thousands graph (1000-99999)
        # Tamil: ஆயிரம் (aayiram)
        suffix_thousands = pynutil.insert(" ஆயிரம்")
        graph_thousands = create_graph_suffix(digit, suffix_thousands, 3)
        graph_thousands |= create_larger_number_graph(digit, suffix_thousands, 2, digit)
        graph_thousands |= create_larger_number_graph(digit, suffix_thousands, 1, teens_ties)
        graph_thousands |= create_larger_number_graph(
            digit, suffix_thousands, 0, graph_all_hundreds
        )
        graph_thousands.optimize()
        self.graph_thousands = graph_thousands

        graph_ten_thousands = create_graph_suffix(teens_and_ties, suffix_thousands, 3)
        graph_ten_thousands |= create_larger_number_graph(
            teens_and_ties, suffix_thousands, 2, digit
        )
        graph_ten_thousands |= create_larger_number_graph(
            teens_and_ties, suffix_thousands, 1, teens_ties
        )
        graph_ten_thousands |= create_larger_number_graph(
            teens_and_ties, suffix_thousands, 0, graph_all_hundreds
        )
        graph_ten_thousands.optimize()
        self.graph_ten_thousands = graph_ten_thousands

        # Lakhs graph and ten lakhs graph (100000-9999999)
        # Tamil: இலட்சம் (ilatcham)
        suffix_lakhs = pynutil.insert(" இலட்சம்")
        graph_lakhs = create_graph_suffix(digit, suffix_lakhs, 5)
        graph_lakhs |= create_larger_number_graph(digit, suffix_lakhs, 4, digit)
        graph_lakhs |= create_larger_number_graph(digit, suffix_lakhs, 3, teens_ties)
        graph_lakhs |= create_larger_number_graph(digit, suffix_lakhs, 2, graph_all_hundreds)
        graph_lakhs |= create_larger_number_graph(digit, suffix_lakhs, 1, graph_thousands)
        graph_lakhs |= create_larger_number_graph(digit, suffix_lakhs, 0, graph_ten_thousands)
        graph_lakhs.optimize()
        self.graph_lakhs = graph_lakhs

        graph_ten_lakhs = create_graph_suffix(teens_and_ties, suffix_lakhs, 5)
        graph_ten_lakhs |= create_larger_number_graph(teens_and_ties, suffix_lakhs, 4, digit)
        graph_ten_lakhs |= create_larger_number_graph(teens_and_ties, suffix_lakhs, 3, teens_ties)
        graph_ten_lakhs |= create_larger_number_graph(
            teens_and_ties, suffix_lakhs, 2, graph_all_hundreds
        )
        graph_ten_lakhs |= create_larger_number_graph(
            teens_and_ties, suffix_lakhs, 1, graph_thousands
        )
        graph_ten_lakhs |= create_larger_number_graph(
            teens_and_ties, suffix_lakhs, 0, graph_ten_thousands
        )
        graph_ten_lakhs.optimize()
        self.graph_ten_lakhs = graph_ten_lakhs

        # Crores graph and ten crores graph (10000000+)
        # Tamil: கோடி (kodi)
        suffix_crores = pynutil.insert(" கோடி")
        graph_crores = create_graph_suffix(digit, suffix_crores, 7)
        graph_crores |= create_larger_number_graph(digit, suffix_crores, 6, digit)
        graph_crores |= create_larger_number_graph(digit, suffix_crores, 5, teens_ties)
        graph_crores |= create_larger_number_graph(digit, suffix_crores, 4, graph_all_hundreds)
        graph_crores |= create_larger_number_graph(digit, suffix_crores, 3, graph_thousands)
        graph_crores |= create_larger_number_graph(digit, suffix_crores, 2, graph_ten_thousands)
        graph_crores |= create_larger_number_graph(digit, suffix_crores, 1, graph_lakhs)
        graph_crores |= create_larger_number_graph(digit, suffix_crores, 0, graph_ten_lakhs)
        graph_crores.optimize()
        self.graph_crores = graph_crores

        graph_ten_crores = create_graph_suffix(teens_and_ties, suffix_crores, 7)
        graph_ten_crores |= create_larger_number_graph(teens_and_ties, suffix_crores, 6, digit)
        graph_ten_crores |= create_larger_number_graph(teens_and_ties, suffix_crores, 5, teens_ties)
        graph_ten_crores |= create_larger_number_graph(
            teens_and_ties, suffix_crores, 4, graph_all_hundreds
        )
        graph_ten_crores |= create_larger_number_graph(
            teens_and_ties, suffix_crores, 3, graph_thousands
        )
        graph_ten_crores |= create_larger_number_graph(
            teens_and_ties, suffix_crores, 2, graph_ten_thousands
        )
        graph_ten_crores |= create_larger_number_graph(
            teens_and_ties, suffix_crores, 1, graph_lakhs
        )
        graph_ten_crores |= create_larger_number_graph(
            teens_and_ties, suffix_crores, 0, graph_ten_lakhs
        )
        graph_ten_crores.optimize()
        self.graph_ten_crores = graph_ten_crores

        # Handle leading zeros (e.g., 05 -> பூஜ்யம் ஐந்து)
        single_digit = digit | zero
        graph_leading_zero = zero + insert_space + single_digit
        graph_leading_zero = pynutil.add_weight(graph_leading_zero, 0.5)

        # Combine all number patterns efficiently
        # Support both Tamil digits and Arabic digits
        # Tamil digits go directly to final_graph
        tamil_final_graph = (
            digit
            | zero
            | teens_and_ties
            | graph_all_hundreds
            | graph_thousands
            | graph_ten_thousands
            | graph_lakhs
            | graph_ten_lakhs
            | graph_crores
            | graph_ten_crores
            | graph_leading_zero
        ).optimize()

        # Arabic digits: convert to Tamil, then apply the same graph
        arabic_digit_input = pynini.closure(DIGIT, 1)
        arabic_final_graph = pynini.compose(
            arabic_digit_input, arabic_to_tamil_number @ tamil_final_graph
        ).optimize()

        # Any 3-digit international grouping (1,000 / 1,000,000) is read in the
        # Indian idiom after dropping the commas: 1,000,000 -> பத்து இலட்சம்.
        intl_comma_pattern = (
            pynini.closure(any_digit, 1, 3) + pynini.closure(comma + three_digits, 1)
        ).optimize()
        intl_as_indian = (
            pynini.compose(intl_comma_pattern, delete_commas)
            @ (tamil_final_graph | (arabic_to_tamil_number @ tamil_final_graph))
        ).optimize()

        # Indian comma/default handling.
        tamil_with_commas = (
            pynini.compose(indian_comma_pattern, delete_commas) @ tamil_final_graph
        ).optimize()
        tamil_final_with_commas = (
            pynutil.add_weight(intl_as_indian, -0.1)
            | pynutil.add_weight(tamil_with_commas, -0.1)
            | tamil_final_graph
        )

        # Arabic with Indian commas.
        arabic_with_commas = (
            pynini.compose(indian_comma_pattern, delete_commas)
            @ arabic_to_tamil_number
            @ tamil_final_graph
        ).optimize()
        arabic_final_with_commas = (
            pynutil.add_weight(intl_as_indian, -0.1)
            | pynutil.add_weight(arabic_with_commas, -0.1)
            | arabic_final_graph
        )

        # Combine both Tamil and Arabic digit paths (both with comma support)
        final_graph = tamil_final_with_commas | arabic_final_with_commas

        # Sandhi: after a stem ending ற்று, a ப/த-initial word doubles its
        # consonant and joins, e.g. நூற்று பத்து -> நூற்றுப்பத்து (110).
        sandhi = pynini.cdrewrite(
            pynini.union(pynini.cross(" ப", "ப்ப"), pynini.cross(" த", "த்த")),
            "ற்று",
            "",
            SIGMA,
        )

        # Scale-word style: exactly one thousand is bare ஆயிரம்; a counting
        # prefix before a scale word is ஒரு, not ஒன்று (ஒரு இலட்சம், ஒரு கோடி).
        # Before a following கோடி the thousand keeps its exact form (ஆயிரம் கோடி).
        exact_end = pynini.union("[EOS]", " கோடி")
        drop_one_exact = pynini.cdrewrite(
            pynini.cross("ஒன்று ஆயிரம்", "ஆயிரம்"), "[BOS]", exact_end, SIGMA
        )
        drop_one_rest = pynini.cdrewrite(
            pynini.cross("ஒன்று ஆயிரம்", "ஆயிரத்து"), "[BOS]", " ", SIGMA
        )
        oru_scales = pynini.cdrewrite(
            pynini.cross("ஒன்று ", "ஒரு "),
            "[BOS]",
            pynini.union("இலட்சம்", "கோடி"),
            SIGMA,
        )

        # Thousands fuse with their digit: இரண்டு ஆயிரம் -> இரண்டாயிரம், and with a
        # remainder இரண்டாயிரத்து (2024 -> இரண்டாயிரத்து இருபத்துநான்கு).
        word_boundary = pynini.union("[BOS]", " ")
        fuse_exact = SIGMA
        fuse_rest = SIGMA
        for d in ["இரண்டு", "மூன்று", "நான்கு", "ஐந்து", "ஆறு", "ஏழு", "எட்டு", "ஒன்பது"]:
            stem = d[:-1] + "ா"
            fuse_exact @= pynini.cdrewrite(
                pynini.cross(f"{d} ஆயிரம்", f"{stem}யிரம்"), word_boundary, exact_end, SIGMA
            )
            fuse_rest @= pynini.cdrewrite(
                pynini.cross(f"{d} ஆயிரம்", f"{stem}யிரத்து"), word_boundary, " ", SIGMA
            )

        style = (
            sandhi @ drop_one_exact @ drop_one_rest @ oru_scales @ fuse_exact @ fuse_rest
        ).optimize()

        # Normalize spacing inside the graph itself (some sub-graphs insert a
        # leading space), so inversion for ITN sees the same strings TN emits.
        squeeze = pynini.cdrewrite(pynini.cross(pynini.closure(" ", 2), " "), "", "", SIGMA)
        strip_leading = pynini.cdrewrite(pynutil.delete(pynini.closure(" ", 1)), "[BOS]", "", SIGMA)
        final_graph = (final_graph @ squeeze @ strip_leading).optimize()

        # ITN accepts both the styled forms and the plain spaced forms, minus the
        # leading-zero pair: ITN must read பூஜ்யம் ஒன்று as the digit run 0 1, not 01.
        raw_final_graph = final_graph
        final_graph = (final_graph @ style).optimize()
        not_leading_zero = pynini.difference(
            pynini.closure(CHAR), pynini.accep("பூஜ்யம் ") + pynini.closure(CHAR)
        )
        self.itn_input_graph = (
            pynini.union(raw_final_graph, final_graph) @ not_leading_zero
        ).optimize()

        # A sign is a field, so the verbalizer renders it and ITN can invert it.
        optional_sign_graph = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" ')
            | pynutil.insert("positive: ") + pynini.cross("+", '"true" '),
            0,
            1,
        )

        self.final_graph = final_graph

        # Digit-by-digit fallback for shapes the number grammar rejects, e.g.
        # leading-zero runs (007) and digit strings beyond the crore range.
        digit_word = pynini.union(digit, zero)
        digit_by_digit = (
            (digit_word | (arabic_to_tamil_digit @ digit_word))
            + pynini.closure(insert_space + (digit_word | (arabic_to_tamil_digit @ digit_word)), 1)
        ).optimize()
        self.digit_by_digit = digit_by_digit
        # A comma-grouped run beyond the crore range (1,00,00,00,000) also falls back
        # to digit-by-digit instead of being split at a comma.
        commas_digit_by_digit = (
            pynini.compose(indian_comma_pattern | intl_comma_pattern, delete_commas)
            @ digit_by_digit
        ).optimize()

        # Case-suffixed numbers, e.g. 2024ல் -> ...இருபத்துநான்கில். The locative
        # -இல் replaces the final -உ; ம்-final scale words take -த்தில்.
        locative_ending = pynini.union(pynini.cross("ு", "ில்"), pynini.cross("ம்", "த்தில்"))
        suffixed_locative = (final_graph @ (SIGMA + locative_ending)) + pynutil.delete(
            pynini.union("ல்", "இல்")
        )
        # Oblique த்தில் written out (1000த்தில் -> ஆயிரத்தில்).
        suffixed_oblique = (final_graph @ (SIGMA + pynini.cross("ம்", "த்தில்"))) + pynutil.delete(
            "த்தில்"
        )
        # Dative க்கு/க்குள் and plural கள்/களில் attach to the number word;
        # ம்-final scale words take -த்து before the dative (இலட்சத்துக்கு).
        dative = pynini.union(pynini.accep("க்கு"), pynini.accep("க்குள்"), pynini.accep("க்கும்"))
        not_m_final = pynini.closure(CHAR) + pynini.difference(CHAR, pynini.accep("்"))
        suffixed_attach = (final_graph @ not_m_final) + dative
        suffixed_attach |= (final_graph @ (SIGMA + pynini.cross("ம்", "த்து"))) + dative
        suffixed_attach |= final_graph + pynini.union(pynini.accep("கள்"), pynini.accep("களில்"))
        # Inclusive உம்: பத்து + உம் -> பத்தும்; இலட்சம் + உம் -> இலட்சமும்.
        suffixed_attach |= (final_graph @ (SIGMA + pynini.accep("ு"))) + pynini.cross("உம்", "ம்")
        suffixed_attach |= (final_graph @ (SIGMA + pynini.cross("ம்", "மு"))) + pynini.cross(
            "உம்", "ம்"
        )
        # Adverbial ஆக: 5ஆக -> ஐந்தாக.
        aa_stem = final_graph @ (
            SIGMA + pynini.union(pynini.cross("ு", "ா"), pynini.cross("ம்", "மா"))
        )
        suffixed_attach |= aa_stem + pynutil.delete("ஆ") + pynini.accep("க")

        # Remaining case suffixes: the final -உ takes the vowel of the suffix, a
        # ம்-final scale word takes the oblique -த்த- (ஐந்தால், ஆயிரத்தால்).
        def with_vowel(sign: str, oblique: str) -> pynini.Fst:
            return final_graph @ (
                SIGMA + pynini.union(pynini.cross("ு", sign), pynini.cross("ம்", oblique))
            )

        # Instrumental ஆல் (also written as the vowel sign: 5ால்).
        suffixed_attach |= with_vowel("ா", "த்தா") + pynutil.delete("ஆ") + pynini.accep("ல்")
        suffixed_attach |= with_vowel("", "த்த") + pynini.accep("ால்")
        # Inclusive written with the vowel sign: 5ும் -> ஐந்தும்.
        suffixed_attach |= with_vowel("", "ம") + pynini.accep("ும்")
        # Sociative ஓடு / உடன்.
        suffixed_attach |= with_vowel("ோ", "த்தோ") + pynutil.delete("ஓ") + pynini.accep("டு")
        suffixed_attach |= with_vowel("ு", "த்து") + pynutil.delete("உ") + pynini.accep("டன்")
        # Accusative ஐ.
        suffixed_attach |= with_vowel("ை", "த்தை") + pynutil.delete("ஐ")
        # Genitive இன்/ன் and ablative (இ)லிருந்து.
        optional_i = pynutil.delete(pynini.closure("இ", 0, 1))
        suffixed_attach |= with_vowel("ி", "த்தி") + optional_i + pynini.accep("ன்")
        suffixed_attach |= with_vowel("ி", "த்தி") + optional_i + pynini.accep("லிருந்து")
        # Emphatic தான் simply attaches.
        suffixed_attach |= final_graph + pynini.accep("தான்")

        # ITN inverts this union to recover 2024ல் from இரண்டாயிரத்து இருபத்துநான்கில்.
        self.itn_suffixed_graph = pynini.union(
            suffixed_locative, suffixed_oblique, suffixed_attach
        ).optimize()

        tagged_integer = (
            self.final_graph
            | pynutil.add_weight(suffixed_locative, 0.1)
            | pynutil.add_weight(suffixed_oblique, 0.1)
            | pynutil.add_weight(suffixed_attach, 0.1)
            | pynutil.add_weight(digit_by_digit, 20.0)
            | pynutil.add_weight(commas_digit_by_digit, 20.0)
        )
        final_graph = (
            optional_sign_graph
            + pynutil.insert('integer: "')
            + tagged_integer
            + pynutil.insert('"')
        )
        final_graph = self.add_tokens(final_graph)
        self.fst = final_graph.optimize()
