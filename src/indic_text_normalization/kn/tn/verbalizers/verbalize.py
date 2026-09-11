"""
Union of all Kannada TN per-class verbalizers, and the sentence verbalizer that glues the
range word onto the lower bound.
"""

from indic_text_normalization.core import tn_verbalizers as generic
from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.sentence import SentenceVerbalizeFst
from indic_text_normalization.kn.constants import MINUS_WORD, PLUS_WORD, RANGE_WORD
from indic_text_normalization.kn.morphology import range_sandhi
from indic_text_normalization.kn.tn.verbalizers.decimal import DecimalFst
from indic_text_normalization.kn.tn.verbalizers.fraction import FractionFst
from indic_text_normalization.kn.tn.verbalizers.measure import MeasureFst
from indic_text_normalization.kn.tn.verbalizers.money import MoneyFst
from indic_text_normalization.kn.tn.verbalizers.time import TimeFst


class VerbalizeFst(GraphFst):
    """
    Union of all per-class TN verbalizer grammars.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize", kind="verbalize", deterministic=deterministic)

        self.fst = (
            generic.CardinalFst(minus_word=MINUS_WORD, plus_word=PLUS_WORD).fst
            | DecimalFst(deterministic=deterministic).fst
            | TimeFst(deterministic=deterministic).fst
            | generic.DateFst(deterministic=deterministic).fst
            | MoneyFst(deterministic=deterministic).fst
            | MeasureFst(deterministic=deterministic).fst
            | generic.RangeFst(range_word=RANGE_WORD).fst
            | FractionFst(deterministic=deterministic).fst
            | generic.OrdinalFst(deterministic=deterministic).fst
            | generic.TelephoneFst(deterministic=deterministic).fst
            | generic.WhiteListFst(deterministic=deterministic).fst
        )


class SentenceFst(GraphFst):
    """
    The Kannada sentence verbalizer: the shared one, then ರಿಂದ glued onto the word before
    it with the ablative sandhi (ಹತ್ತು ರಿಂದ ಇಪ್ಪತ್ತು -> ಹತ್ತರಿಂದ ಇಪ್ಪತ್ತು, ಐದು ರೂಪಾಯಿ ರಿಂದ ->
    ಐದು ರೂಪಾಯಿಯಿಂದ). A bare ರಿಂದ is never a word of its own, so the rewrite is safe.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="verbalize_final", kind="verbalize", deterministic=deterministic)

        sentence = SentenceVerbalizeFst(
            VerbalizeFst(deterministic=deterministic), generic.WordFst(deterministic=deterministic)
        )
        self.fst = (sentence.fst @ range_sandhi()).optimize()
