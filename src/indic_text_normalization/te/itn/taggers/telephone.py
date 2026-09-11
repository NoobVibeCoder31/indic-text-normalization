"""
ITN tagger converting spoken digit sequences to telephone numbers.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path
from indic_text_normalization.core.graph_utils import delete_space, DIGIT, GraphFst
from indic_text_normalization.te.constants import CASE_SUFFIXES, LANG
from indic_text_normalization.te.itn.taggers.cardinal import CardinalFst

digit_words = pynini.invert(pynini.string_file(data_path(LANG, "telephone/number.tsv"))).optimize()


class TelephoneFst(GraphFst):
    """
    Finite state transducer for classifying spoken digit strings, e.g.
        a sequence of ten digit words -> telephone { number_part: "9943206870" }
        ప్లస్ తొంభై ఒకటి ... -> telephone { country_code: "+91" number_part: "..." }
        సున్నా సున్నా ఏడు -> telephone { number_part: "007" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="classify", deterministic=deterministic)

        # The digit table is keyed by Telugu digits; emit ASCII, and accept zero variants.
        to_ascii = pynini.string_map([(chr(0x0C66 + i), str(i)) for i in range(10)])
        digit = pynini.union(
            digit_words @ to_ascii, pynini.cross("సున్న", "0"), pynini.cross("జీరో", "0")
        ).optimize()

        # Three or more digit words in a row are a digit string (phone, PIN, OTP, 007);
        # after a country code the number is a 10-digit mobile or 11-digit landline.
        number = digit + pynini.closure(delete_space + digit, 2)
        cc_number = digit + pynini.closure(delete_space + digit, 9, 10)
        # A case suffix on the last digit word is carried over (…సున్నాకి -> …0కి).
        suffix = pynini.closure(pynini.union(*CASE_SUFFIXES), 0, 1)

        # ప్లస్ followed by one to three digit words, or by a spoken number (తొంభై ఒకటి).
        code_digits = pynini.union(
            digit + pynini.closure(delete_space + digit, 0, 2),
            cardinal.words_to_digits @ pynini.closure(DIGIT, 1, 3),
        )
        country_code = pynutil.insert('country_code: "') + pynini.cross("ప్లస్", "+") + delete_space
        country_code = country_code + code_digits + pynutil.insert('"')

        number_part = pynutil.insert('number_part: "') + number + suffix + pynutil.insert('"')
        cc_number_part = pynutil.insert('number_part: "') + cc_number + suffix + pynutil.insert('"')
        graph = number_part | (country_code + pynutil.insert(" ") + delete_space + cc_number_part)
        # A standalone two- or three-digit country code: ప్లస్ తొంభై ఒకటి -> +91.
        standalone = pynutil.insert('country_code: "') + pynini.cross("ప్లస్", "+") + delete_space
        standalone += pynini.union(
            digit + pynini.closure(delete_space + digit, 1, 2),
            cardinal.words_to_digits @ pynini.closure(DIGIT, 2, 3),
        ) + pynutil.insert('"')
        graph |= pynutil.add_weight(standalone, 0.2)
        self.fst = self.add_tokens(graph).optimize()
