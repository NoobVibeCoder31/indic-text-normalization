"""
Sentence-level assembly shared by every language and both directions: the tokenizer that
wraps each span in ``tokens { ... }`` and the verbalizer that unwraps them again.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    CURRENCY_SYMBOLS,
    SPACE,
    WHITE_SPACE,
    GraphFst,
    convert_space,
    delete_extra_space,
    delete_space,
)
from indic_text_normalization.core.punctuation import PunctuationFst
from indic_text_normalization.core.word import WordFst


class SentenceClassifyFst(GraphFst):
    """
    Tokenize a sentence, tagging every span with a semiotic class or as a word.

    Attributes
    ----------
    classify : ``pynini.Fst``
        Weighted union of the per-class taggers.
    punctuation : ``PunctuationFst``
        Punctuation grammar; marks become their own tokens.
    word : ``WordFst``
        Fallback tagger for spans no class accepts.
    pre_pass : ``pynini.Fst | None``, optional (default = None)
        Spacing rewrites applied to the text before tagging. It is kept separate and
        composed with the input at call time: compiling it into the sentence graph
        triples the graph for a rewrite that costs microseconds per call.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        classify: pynini.Fst,
        *,
        punctuation: PunctuationFst,
        word: WordFst,
        pre_pass: pynini.Fst | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="tokenize_and_classify", kind="classify", deterministic=deterministic)

        punct = (
            pynutil.insert("tokens { ")
            + pynutil.add_weight(punctuation.fst, weight=2.1)
            + pynutil.insert(" }")
        )
        punct = pynini.closure(
            pynini.union(
                pynini.compose(pynini.closure(WHITE_SPACE, 1), delete_extra_space),
                (pynutil.insert(SPACE) + punct),
            ),
            1,
        )

        classify = pynini.union(classify, pynutil.add_weight(word.fst, 100))
        token = pynutil.insert("tokens { ") + classify + pynutil.insert(" }")
        token_plus_punct = (
            pynini.closure(punct + pynutil.insert(SPACE))
            + token
            + pynini.closure(pynutil.insert(SPACE) + punct)
        )

        graph = token_plus_punct + pynini.closure(
            pynini.union(
                pynini.compose(pynini.closure(WHITE_SPACE, 1), delete_extra_space),
                (pynutil.insert(SPACE) + punct + pynutil.insert(SPACE)),
            )
            + token_plus_punct
        )

        graph = delete_space + graph + delete_space
        graph = pynini.union(graph, punct)

        self.pre_pass = pre_pass.optimize() if pre_pass is not None else None
        self.fst = graph.optimize()


class SentenceVerbalizeFst(GraphFst):
    """
    Verbalize a whole tagged sentence, e.g.
        tokens { cardinal { integer: "23" } } tokens { name: "பேர்" } -> 23 பேர்

    Attributes
    ----------
    verbalize : ``GraphFst``
        Union of the per-class verbalizers.
    word : ``GraphFst``
        Verbalizer for plain ``name`` tokens.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(self, verbalize: GraphFst, word: GraphFst, deterministic: bool = True) -> None:
        super().__init__(name="verbalize_final", kind="verbalize", deterministic=deterministic)

        types = verbalize.fst | word.fst
        graph = (
            pynutil.delete("tokens")
            + delete_space
            + pynutil.delete("{")
            + delete_space
            + types
            + delete_space
            + pynutil.delete("}")
        )
        graph = delete_space + pynini.closure(graph + delete_extra_space) + graph + delete_space

        self.fst = graph.optimize()


def written_number_passthrough(
    *, digit: pynini.Fst, letter: pynini.Fst, scale_words: list[str]
) -> pynini.Fst:
    """
    Tagger for an already-written number that ITN must return unchanged.

    ITN's own output re-fed (12.5%, 10-20, +91 9876543210, ₹5 కోట్లు, 2024లో) must not be
    split into punctuation and digits or re-read; a sign, a currency symbol, a glued
    case suffix and a kept scale word all travel with the digits.

    Parameters
    ----------
    digit : ``pynini.Fst``
        Acceptor for one digit in either script.
    letter : ``pynini.Fst``
        Acceptor for one letter of the language, for a glued case suffix.
    scale_words : ``list[str]``
        Scale words the written idiom keeps after a number (కోట్లు, லட்சம்).

    Returns
    -------
    ``pynini.Fst``
        A ``name: "..."`` tagger for the written number.
    """
    number = (
        pynini.closure(pynini.union("-", "+"), 0, 1)
        + pynini.closure(pynini.union(*CURRENCY_SYMBOLS), 0, 1)
        + pynini.closure(digit, 1)
        + pynini.closure(pynini.union(*".:,/-") + pynini.closure(digit, 1))
        + pynini.closure("%", 0, 1)
        + pynini.closure(letter)
        + pynini.closure(" " + pynini.union(*scale_words), 0, 1)
    )
    # The space before a scale word travels as U+00A0 NO-BREAK SPACE, as in every other
    # multi-word value; the word verbalizer turns it back into a space.
    return (pynutil.insert('name: "') + convert_space(number) + pynutil.insert('"')).optimize()
