"""
TN tagger for Indian telephone numbers, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst, delete_space, insert_space
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.utils import data_path, load_labels


class TelephoneFst(GraphFst):
    """
    Finite state transducer for classifying telephone numbers, e.g.
        9943206870 -> telephone { number_part: "తొమ్మిది తొమ్మిది నాలుగు ..." }
        +91 9876543210 -> telephone { country_code: "ప్లస్ తొమ్మిది ఒకటి" number_part: "..." }
        044-28230000 -> telephone { number_part: "సున్నా నాలుగు నాలుగు రెండు ..." }
        పిన్ కోడ్ 500001 -> telephone { number_part: "పిన్ కోడ్ ఐదు సున్నా ..." }

    Reads ``telephone/number.tsv`` (native digit -> word) and ``telephone/cues.tsv`` (words
    after which a 4-6 digit run reads digit by digit: PIN, OTP).
    """

    def __init__(self, cardinal: CardinalBase, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        digit_to_word = pynini.string_file(data_path(profile.lang, "telephone/number.tsv"))
        single_digit_to_word = pynini.union(
            profile.digits.digit @ digit_to_word, profile.digits.from_ascii @ digit_to_word
        ).optimize()
        natives = [chr(ord(profile.digits.zero) + i) for i in range(10)]
        mobile_first_digit = pynini.union(*"6789", *natives[6:])
        zero_digit = pynini.union("0", natives[0])
        one_word = pynini.union("1", natives[1]) @ single_digit_to_word

        digit_word = single_digit_to_word + insert_space
        last_digit_word = single_digit_to_word
        delete_sep = pynutil.delete(pynini.union("-", " "))
        optional_sep = pynini.closure(delete_sep, 0, 1)

        # A case suffix on the number lands on the last digit word (9876543210కి -> ...సున్నాకి).
        last_digit_suffixed = cardinal.attach_case_suffix(last_digit_word)

        def shapes(last: pynini.Fst) -> tuple[pynini.Fst, pynini.Fst]:
            # 10-digit mobile starting 6-9; a 5-5 split with space or dash is common.
            mobile = (
                (mobile_first_digit @ single_digit_to_word)
                + insert_space
                + pynini.closure(digit_word, 3, 3)
                + digit_word
                + optional_sep
                + pynini.closure(digit_word, 4, 4)
                + last
            )

            # Landline: STD code starting 0 (2-4 digits, optionally in parentheses), a
            # dash or space, then a 6-8 digit subscriber number optionally split once.
            std_digits = (
                (zero_digit @ single_digit_to_word)
                + insert_space
                + pynini.closure(digit_word, 1, 3)
            )
            std_code = std_digits | (pynutil.delete("(") + std_digits + pynutil.delete(")"))
            # A hyphen split inside the subscriber is only the 4-4 shape (2823-0000), so a
            # date like 01-04-2024 never reads as a landline.
            subscriber = (
                pynini.closure(digit_word, 2, 4)
                + pynini.closure(pynutil.delete(" "), 0, 1)
                + pynini.closure(digit_word, 2, 3)
                + last
            )
            subscriber |= (
                pynini.closure(digit_word, 4, 4)
                + pynutil.delete("-")
                + pynini.closure(digit_word, 3, 3)
                + last
            )
            landline = std_code + optional_sep + subscriber

            # Toll-free: 1800-XXX-XXXX / 1-800-XXX-XXXX.
            toll_free = (
                one_word
                + insert_space
                + optional_sep
                + pynini.closure(digit_word, 3, 3)
                + delete_sep
                + pynini.closure(digit_word, 3, 3)
                + delete_sep
                + pynini.closure(digit_word, 3, 3)
                + last
            )
            # Toll-free 1800-11-4000 / 1800 11 4000: 1800 + 2-3 digits + 3-4 digits.
            toll_free |= (
                one_word
                + insert_space
                + pynini.closure(digit_word, 3, 3)
                + delete_sep
                + pynini.closure(digit_word, 2, 3)
                + delete_sep
                + pynini.closure(digit_word, 2, 3)
                + last
            )

            # After a country code the STD code drops its leading zero: +91-44-28230000,
            # optionally in parentheses: +91 (44) 2823 0000.
            std_digits_no_zero = pynini.closure(digit_word, 2, 4)
            std_no_zero = (
                (
                    std_digits_no_zero
                    | pynutil.delete("(") + std_digits_no_zero + pynutil.delete(")")
                )
                + delete_sep
                + subscriber
            )
            return pynini.union(mobile, landline, toll_free), std_no_zero

        plain, cc_landline = shapes(last_digit_word)
        suffixed, cc_landline_suffixed = shapes(last_digit_suffixed)

        country_code = (
            pynutil.insert('country_code: "')
            + pynini.cross("+", profile.plus_word)
            + insert_space
            + pynini.closure(digit_word, 0, 2)
            + last_digit_word
            + pynutil.insert('" ')
            + pynini.closure(delete_space | pynutil.delete("-"), 0, 1)
        )

        def number_part(inner: pynini.Fst) -> pynini.Fst:
            return pynutil.insert('number_part: "') + inner + pynutil.insert('"')

        graph = pynini.union(
            pynutil.add_weight(country_code + number_part(plain | cc_landline), 0.1),
            pynutil.add_weight(number_part(plain), 0.1),
            pynutil.add_weight(country_code + number_part(suffixed | cc_landline_suffixed), 0.2),
            pynutil.add_weight(number_part(suffixed), 0.2),
        )

        # PIN codes and OTPs read digit by digit after their cue word (పిన్ కోడ్ 500001).
        cues = [row[0] for row in load_labels(data_path(profile.lang, "telephone/cues.tsv"))]
        cued_digits = (
            pynutil.insert('number_part: "')
            + pynini.union(*cues)
            + pynini.accep(" ")
            + pynini.closure(digit_word, 3, 5)
            + last_digit_word
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(cued_digits, 0.1)

        # A standalone +N... (no number following) reads as <plus> <number>, digit by digit
        # when the run has leading zeros or exceeds the cardinal's range (+000, +007).
        standalone_cc = (
            pynutil.insert('country_code: "')
            + pynini.cross("+", profile.plus_word)
            + insert_space
            + (cardinal.final_graph | pynutil.add_weight(cardinal.digit_by_digit, 1.0))
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(standalone_cc, 0.3)

        self.final = graph.optimize()
        self.fst = self.add_tokens(self.final)
