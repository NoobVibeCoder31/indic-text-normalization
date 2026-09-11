"""
Assembly of a language's ITN taggers into the sentence classifier, with the class weights
every language shares.
"""

from collections.abc import Sequence

from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.profile import LanguageProfile
from indic_text_normalization.core.punctuation import PunctuationFst
from indic_text_normalization.core.scales import kept_scale_words
from indic_text_normalization.core.sentence import SentenceClassifyFst, written_number_passthrough
from indic_text_normalization.core.word import WordFst


class ItnClassifyFst(SentenceClassifyFst):
    """
    Compose a language's ITN taggers into a single sentence classifier.

    Attributes
    ----------
    profile : ``LanguageProfile``
        The language's profile.
    cardinal, decimal, fraction, ordinal, date, time, money, telephone, prose : ``GraphFst``
        The per-class taggers.
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
        ordinal: GraphFst,
        date: GraphFst,
        time: GraphFst,
        money: GraphFst,
        telephone: GraphFst,
        prose: GraphFst,
        extra: Sequence[tuple[GraphFst, float]] = (),
        deterministic: bool = True,
    ) -> None:
        punctuation = PunctuationFst(profile.lang, deterministic=deterministic)
        written = written_number_passthrough(
            digit=profile.any_digit,
            letter=profile.letter,
            scale_words=kept_scale_words(profile.lang),
        )
        classify = (
            pynutil.add_weight(written, 0.8)
            | pynutil.add_weight(prose.fst, 1.0)
            | pynutil.add_weight(telephone.fst, 0.9)
            | pynutil.add_weight(date.fst, 1.04)
            | pynutil.add_weight(time.fst, 1.05)
            | pynutil.add_weight(fraction.fst, 1.06)
            | pynutil.add_weight(money.fst, 1.07)
            | pynutil.add_weight(decimal.fst, 1.08)
            | pynutil.add_weight(ordinal.fst, 1.09)
            | pynutil.add_weight(cardinal.fst, 1.1)
        )
        for tagger, weight in extra:
            classify |= pynutil.add_weight(tagger.fst, weight)
        word = WordFst(punctuation, script=profile.block, deterministic=deterministic)
        super().__init__(classify, punctuation=punctuation, word=word, deterministic=deterministic)
