"""
TN tagger for fractions and vulgar-fraction signs, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase


class FractionFst(GraphFst):
    """
    Finite state transducer for classifying fractions, e.g.
        3/4 -> fraction { numerator: "మూడు" denominator: "నాలుగు" }
        2 3/4 -> fraction { integer_part: "రెండు" numerator: "మూడు" denominator: "నాలుగు" }
        ½ -> fraction { word: "అర" }
        1½ -> fraction { word: "ఒకటిన్నర" }
        2¾ -> fraction { word: "రెండు మరియు ముప్పావు" }

    Attributes
    ----------
    cardinal : ``CardinalBase``
        The language's cardinal.
    vulgar_words : ``dict[str, str]``
        Spoken word for each of U+00BD VULGAR FRACTION ONE HALF, U+00BC ONE QUARTER and
        U+00BE THREE QUARTERS.
    and_word : ``str | None``
        Conjunction between an integer and a following fraction word (రెండు మరియు ముప్పావు),
        or None when the language has no such reading.
    part_nouns : ``tuple[str, ...]``
        Written nouns after a fraction that the verbalizer speaks itself (వంతు), absorbed.
    mixed_vulgar : ``pynini.Fst | None``, optional (default = None)
        Transducer from a written integer plus a vulgar sign (1½, 12 ½, 2¾) to the fused
        spoken word (ఒకటిన్నర, ഒന്നര, रണ്ടേമുക്കാൽ, डेढ़); it outranks the ``and_word``
        reading where it applies.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: CardinalBase,
        *,
        vulgar_words: dict[str, str],
        and_word: str | None,
        part_nouns: tuple[str, ...] = (),
        mixed_vulgar: pynini.Fst | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="fraction", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        cardinal_graph = cardinal.final_graph
        any_digit = profile.any_digit
        zero = pynini.union("0", profile.digits.zero)

        # A zero or zero-led denominator (1/0, 15/06) is not a fraction.
        non_zero_led = pynini.difference(
            pynini.closure(any_digit, 1), zero + pynini.closure(any_digit)
        ).optimize()
        denominator_graph = pynini.compose(non_zero_led, cardinal_graph).optimize()

        integer = pynutil.insert('integer_part: "') + cardinal_graph + pynutil.insert('"')
        # A zero-led numerator (06/24) is a date fragment, not a fraction.
        numerator_input = pynini.difference(
            pynini.closure(any_digit, 1), zero + pynini.closure(any_digit, 1)
        ).optimize()
        numerator = (
            pynutil.insert('numerator: "')
            + pynini.compose(numerator_input, cardinal_graph)
            + (pynini.cross("/", '" ') | pynini.cross(" / ", '" '))
        )
        denominator = pynutil.insert('denominator: "') + denominator_graph + pynutil.insert('"')
        part_noun = pynini.accep("")
        if part_nouns:
            part_noun = pynini.closure(pynutil.delete(" " + pynini.union(*part_nouns)), 0, 1)

        graph = pynini.closure(integer + pynini.accep(" "), 0, 1) + numerator + denominator
        graph += part_noun
        optional_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" '), 0, 1
        )
        graph = optional_negative + graph

        # Vulgar signs read as words; with an integer, "N <and> <word>" unless the
        # language fuses the half onto the number.
        optional_space = pynutil.delete(pynini.closure(" ", 0, 1))
        vulgar_word = pynini.union(*[pynini.cross(s, w) for s, w in vulgar_words.items()])
        word = vulgar_word
        if and_word is not None:
            word |= cardinal_graph + optional_space + pynutil.insert(f" {and_word} ") + vulgar_word
        if mixed_vulgar is not None:
            word |= pynutil.add_weight(mixed_vulgar, -0.1)
        word += part_noun
        graph |= optional_negative + pynutil.insert('word: "') + word + pynutil.insert('"')

        self.graph = graph
        self.fst = self.add_tokens(self.graph).optimize()
