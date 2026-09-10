"""
Assembly of a language's TN taggers into the sentence classifier, with the class weights
every language shares.
"""

from collections.abc import Sequence

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.profile import LanguageProfile
from indic_text_normalization.core.punctuation import PunctuationFst
from indic_text_normalization.core.sentence import SentenceClassifyFst
from indic_text_normalization.core.whitelist import WhiteListFst
from indic_text_normalization.core.word import WordFst


class TnClassifyFst(SentenceClassifyFst):
    """
    Compose a language's TN taggers into a single sentence classifier.

    Attributes
    ----------
    profile : ``LanguageProfile``
        The language's profile.
    cardinal, decimal, fraction, measure, time, date, money, telephone, ordinal, range : ``GraphFst``
        The per-class taggers.
    pre_pass : ``pynini.Fst``
        Spacing rewrites composed with the text before tagging.
    extra : ``Sequence[tuple[GraphFst, float]]``, optional (default = ())
        Additional language-specific taggers with their weights.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        profile: LanguageProfile,
        *,
        cardinal: GraphFst,
        decimal: GraphFst,
        fraction: GraphFst,
        measure: GraphFst,
        time: GraphFst,
        date: GraphFst,
        money: GraphFst,
        telephone: GraphFst,
        ordinal: GraphFst,
        range: GraphFst,
        pre_pass: pynini.Fst,
        extra: Sequence[tuple[GraphFst, float]] = (),
        deterministic: bool = True,
    ) -> None:
        whitelist = WhiteListFst(profile.lang, deterministic=deterministic)
        punctuation = PunctuationFst(profile.lang, speak_equals=True, deterministic=deterministic)

        classify = (
            pynutil.add_weight(whitelist.fst, 1.01)
            | pynutil.add_weight(telephone.fst, 0.5)
            | pynutil.add_weight(measure.fst, 1.03)
            | pynutil.add_weight(date.fst, 1.04)
            | pynutil.add_weight(time.fst, 1.05)
            | pynutil.add_weight(fraction.fst, 1.06)
            | pynutil.add_weight(decimal.fst, 1.08)
            | pynutil.add_weight(range.fst, 1.09)
            | pynutil.add_weight(cardinal.fst, 1.1)
            | pynutil.add_weight(money.fst, 1.1)
            | pynutil.add_weight(ordinal.fst, 1.1)
        )
        for tagger, weight in extra:
            classify |= pynutil.add_weight(tagger.fst, weight)
        word = WordFst(
            punctuation, script=profile.block, pass_urls=True, deterministic=deterministic
        )
        super().__init__(
            classify,
            punctuation=punctuation,
            word=word,
            pre_pass=pre_pass,
            deterministic=deterministic,
        )
