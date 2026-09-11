"""
ITN tagger converting spoken digit sequences to telephone numbers, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst, delete_space
from indic_text_normalization.core.itn_taggers.cardinal import ItnCardinalFst
from indic_text_normalization.core.utils import data_path


class ItnTelephoneFst(GraphFst):
    """
    Finite state transducer for classifying spoken digit strings, e.g.
        a sequence of ten digit words -> telephone { number_part: "9943206870" }
        ప్లస్ తొంభై ఒకటి ... -> telephone { country_code: "+91" number_part: "..." }
        సున్నా సున్నా ఏడు -> telephone { number_part: "007" }

    Attributes
    ----------
    cardinal : ``ItnCardinalFst``
        The language's ITN cardinal.
    zero_words : ``tuple[str, ...]``, optional (default = ())
        Spoken zero variants beyond the telephone table's word (సున్న, జీరో).
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: ItnCardinalFst,
        *,
        zero_words: tuple[str, ...] = (),
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="telephone", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        digit_words = pynini.invert(
            pynini.string_file(data_path(profile.lang, "telephone/number.tsv"))
        ).optimize()
        # The digit table is keyed by native digits; emit ASCII, and accept zero variants.
        digit = digit_words @ profile.digits.to_ascii
        for word in zero_words:
            digit |= pynini.cross(word, "0")
        digit = digit.optimize()

        # A case suffix on the last digit word is carried over (…సున్నాకి -> …0కి,
        # …പൂജ്യത്തിൽ -> …0ൽ), through the cardinal's own suffix reading.
        last = digit
        if profile.case_suffixes:
            suffixed_digit = cardinal.words_to_digits_suffixed @ (
                DIGIT + pynini.closure(profile.letter, 1)
            )
            last = pynini.union(digit, suffixed_digit)
        # Three or more digit words in a row are a digit string (phone, PIN, OTP, 007);
        # after a country code the number is a 10-digit mobile or 11-digit landline.
        number = digit + pynini.closure(delete_space + digit, 1) + delete_space + last
        cc_number = digit + pynini.closure(delete_space + digit, 8, 9) + delete_space + last
        suffix = pynini.accep("")

        plus = pynini.cross(pynini.union(*profile.positive_words), "+")
        # The plus word followed by one to three digit words, or by a spoken number.
        code_digits = pynini.union(
            digit + pynini.closure(delete_space + digit, 0, 2),
            cardinal.words_to_digits @ pynini.closure(DIGIT, 1, 3),
        )
        country_code = pynutil.insert('country_code: "') + plus + delete_space
        country_code = country_code + code_digits + pynutil.insert('"')

        number_part = pynutil.insert('number_part: "') + number + suffix + pynutil.insert('"')
        cc_number_part = pynutil.insert('number_part: "') + cc_number + suffix + pynutil.insert('"')
        graph = number_part | (country_code + pynutil.insert(" ") + delete_space + cc_number_part)
        # A standalone two- or three-digit country code: ప్లస్ తొంభై ఒకటి -> +91.
        standalone = pynutil.insert('country_code: "') + plus + delete_space
        standalone += pynini.union(
            digit + pynini.closure(delete_space + digit, 1, 2),
            cardinal.words_to_digits @ pynini.closure(DIGIT, 2, 3),
        ) + pynutil.insert('"')
        graph |= pynutil.add_weight(standalone, 0.2)
        self.fst = self.add_tokens(graph).optimize()
