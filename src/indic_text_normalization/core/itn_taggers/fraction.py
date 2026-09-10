"""
ITN tagger converting spoken fractions to digits, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    GraphFst,
    delete_space,
    insert_space,
    sequential,
)
from indic_text_normalization.core.itn_taggers.cardinal import ItnCardinalFst


class ItnFractionFst(GraphFst):
    """
    Finite state transducer for classifying spoken fractions, e.g.
        నాలుగింట మూడు వంతులు -> fraction { denominator: "4" numerator: "3" }
        మూడు బై నాలుగు -> fraction { numerator: "3" denominator: "4" }
        రెండు మరియు నాలుగింట మూడు వంతులు -> fraction { integer_part: "2" denominator: "4" numerator: "3" }

    Attributes
    ----------
    cardinal : ``ItnCardinalFst``
        The language's ITN cardinal.
    denominator_to_number : ``pynini.Fst``
        Rewrite from the spoken denominator (in its oblique or locative form: నాలుగింట,
        നാലിൽ, ನಾಲ್ಕರಲ್ಲಿ) back to the plain spoken number.
    part_nouns : ``tuple[str, ...]``
        Written part nouns after the numerator (వంతులు, భాగం), absorbed.
    by_words : ``tuple[str, ...]``
        Words spoken between numerator and denominator in the "N by M" order (బై, बटा).
    and_word : ``str | None``
        Conjunction between an integer and the fraction (రెండు మరియు ...), or None when the
        language has no spaced conjunction.
    mixed : ``pynini.Fst | None``, optional (default = None)
        A language-built reading of mixed numbers, from the spoken phrase to the tagged
        fields (``integer_part: "2" denominator: "4" numerator: "3"``).
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: ItnCardinalFst,
        *,
        denominator_to_number: pynini.Fst | None,
        part_nouns: tuple[str, ...],
        by_words: tuple[str, ...],
        and_word: str | None,
        mixed: pynini.Fst | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="fraction", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        numerator_words = cardinal.words_to_digits
        if profile.counting_one:
            numerator_words = pynini.union(numerator_words, pynini.cross(profile.counting_one, "1"))
        numerator = pynutil.insert('numerator: "') + numerator_words + pynutil.insert('"')
        integer = pynini.Fst()
        if and_word is not None:
            integer = (
                pynutil.insert('integer_part: "')
                + cardinal.words_to_digits
                + pynutil.insert('"')
                + delete_space
                + pynutil.delete(and_word)
                + delete_space
                + insert_space
            )
        optional_part_noun = pynini.accep("")
        if part_nouns:
            optional_part_noun = pynini.closure(
                delete_space + pynutil.delete(pynini.union(*part_nouns)), 0, 1
            )

        graph = pynini.Fst()
        if denominator_to_number is not None:
            # Undo the denominator's oblique form, then read it as a number.
            denominator_words = sequential(denominator_to_number @ cardinal.words_to_digits)
            denominator = pynutil.insert('denominator: "') + denominator_words + pynutil.insert('"')
            graph = denominator + delete_space + insert_space + numerator + optional_part_noun
            graph = pynini.closure(integer, 0, 1) + graph

        if by_words:
            # "N by M" order: మూడు బై నాలుగు, तीन बटा चार -> 3/4.
            by = (
                pynutil.insert('numerator: "')
                + cardinal.words_to_digits
                + pynutil.insert('"')
                + delete_space
                + pynutil.delete(pynini.union(*by_words))
                + delete_space
                + insert_space
                + pynutil.insert('denominator: "')
                + cardinal.words_to_digits
                + pynutil.insert('"')
            )
            graph |= pynini.closure(integer, 0, 1) + by
        if mixed is not None:
            graph |= mixed
        self.fst = self.add_tokens(graph).optimize()
