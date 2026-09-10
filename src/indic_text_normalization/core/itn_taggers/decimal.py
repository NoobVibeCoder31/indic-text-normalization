"""
ITN tagger converting spoken decimals to digits, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst, delete_space, insert_space
from indic_text_normalization.core.itn_taggers.cardinal import (
    ItnCardinalFst,
    half_form_rows,
    optional_sign_field,
)

# Fraction digits of the vulgar signs TN speaks as words.
VULGAR_DIGITS = {"½": "5", "¼": "25", "¾": "75"}


class ItnDecimalFst(GraphFst):
    """
    Finite state transducer for classifying spoken decimals, e.g.
        పన్నెండు దశాంశం ఐదు -> decimal { integer_part: "12" fractional_part: "5" }
        ఒకటిన్నర -> decimal { integer_part: "1" fractional_part: "5" }
        రెండు మరియు ముప్పావు -> decimal { integer_part: "2" fractional_part: "75" }

    Attributes
    ----------
    cardinal : ``ItnCardinalFst``
        The language's ITN cardinal.
    vulgar_words : ``dict[str, str]``
        The TN spoken word of each vulgar sign (½ -> అర), read back as a decimal.
    and_word : ``str | None``
        Conjunction TN puts between an integer and a vulgar word (రెండు మరియు ముప్పావు),
        or None when the language fuses them instead.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: ItnCardinalFst,
        *,
        vulgar_words: dict[str, str],
        and_word: str | None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="decimal", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        # Fractional digits are spoken one to three at a time; a scale word after the
        # fraction is a quantity, never more digits (ఐదు దశాంశం ఐదు లక్షలు -> 5.5 లక్షలు).
        short = cardinal.words_to_digits @ pynini.closure(DIGIT, 1, 3)
        digit_by_digit = short + pynini.closure(delete_space + short)
        self.fractional_digits = digit_by_digit
        point = pynutil.delete(pynini.union(*profile.point_words))

        integer_part = (
            pynutil.insert('integer_part: "') + cardinal.words_to_digits + pynutil.insert('"')
        )
        fractional_part = (
            pynutil.insert('fractional_part: "') + digit_by_digit + pynutil.insert('"')
        )

        optional_sign = optional_sign_field(profile)

        graph = (
            optional_sign
            + integer_part
            + delete_space
            + point
            + delete_space
            + insert_space
            + fractional_part
        )

        # Dotted chains round-trip: ఒకటి దశాంశం రెండు దశాంశం మూడు -> 1.2.3.
        chain_fraction = (
            pynutil.insert('fractional_part: "')
            + digit_by_digit
            + pynini.closure(pynini.cross(f" {profile.point_word} ", ".") + digit_by_digit, 1)
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(
            optional_sign
            + integer_part
            + delete_space
            + point
            + delete_space
            + insert_space
            + chain_fraction,
            -0.1,
        )

        # Fused fractional words: ఒకటిన్నర -> 1.5, పదిన്നర -> 10.5. Bare half/quarter nouns stay.
        half_rows = half_form_rows(profile.lang)
        if half_rows:
            graph |= pynini.union(
                *[
                    pynini.cross(word, f'integer_part: "{ip}" fractional_part: "{fp}"')
                    for word, ip, fp in half_rows
                ]
            )
        # The vulgar-sign readings TN emits: ఐదు మరియు అర -> 5.5, రెండు మరియు ముప్పావు -> 2.75.
        if and_word is not None:
            vulgar = pynini.union(
                *[pynini.cross(word, VULGAR_DIGITS[sign]) for sign, word in vulgar_words.items()]
            )
            graph |= (
                integer_part
                + pynutil.delete(f" {and_word} ")
                + pynutil.insert(' fractional_part: "')
                + vulgar
                + pynutil.insert('"')
            )

        self.fst = self.add_tokens(graph).optimize()
