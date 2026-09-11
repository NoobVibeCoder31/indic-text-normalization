"""
Explicit grammar registry mapping ``(lang, direction)`` to grammar factories.
"""

from collections.abc import Callable
from typing import NamedTuple

from indic_text_normalization.core import itn_verbalizers, tn_verbalizers
from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.sentence import SentenceClassifyFst, SentenceVerbalizeFst

Direction = str

TN = "tn"
ITN = "itn"


class GrammarFactory(NamedTuple):
    """
    Factory pair building the classify and verbalize grammars for one language/direction.
    """

    classify: Callable[[], SentenceClassifyFst]
    verbalize: Callable[[], GraphFst]


def _ta_tn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.ta.tn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _ta_tn_verbalize() -> GraphFst:
    from indic_text_normalization.ta.tn.verbalizers.verbalize import VerbalizeFst

    return SentenceVerbalizeFst(VerbalizeFst(), tn_verbalizers.WordFst())


def _ta_itn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.ta.itn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _ta_itn_verbalize() -> GraphFst:
    from indic_text_normalization.ta.itn.verbalizers.verbalize import VerbalizeFst

    return SentenceVerbalizeFst(VerbalizeFst(), itn_verbalizers.WordFst())


def _te_tn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.te.tn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _te_tn_verbalize() -> GraphFst:
    from indic_text_normalization.te.tn.verbalizers.verbalize import VerbalizeFst

    return SentenceVerbalizeFst(VerbalizeFst(), tn_verbalizers.WordFst())


def _te_itn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.te.itn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _te_itn_verbalize() -> GraphFst:
    from indic_text_normalization.te.itn.verbalizers.verbalize import VerbalizeFst

    return SentenceVerbalizeFst(VerbalizeFst(), itn_verbalizers.WordFst())


def _ml_tn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.ml.tn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _ml_tn_verbalize() -> GraphFst:
    from indic_text_normalization.ml.tn.verbalizers.verbalize import VerbalizeFst

    return SentenceVerbalizeFst(VerbalizeFst(), tn_verbalizers.WordFst())


def _ml_itn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.ml.itn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _ml_itn_verbalize() -> GraphFst:
    from indic_text_normalization.ml.itn.verbalizers.verbalize import VerbalizeFst

    return SentenceVerbalizeFst(VerbalizeFst(), itn_verbalizers.WordFst())


def _kn_tn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.kn.tn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _kn_tn_verbalize() -> GraphFst:
    from indic_text_normalization.kn.tn.verbalizers.verbalize import SentenceFst

    return SentenceFst()


def _kn_itn_classify() -> SentenceClassifyFst:
    from indic_text_normalization.kn.itn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _kn_itn_verbalize() -> GraphFst:
    from indic_text_normalization.kn.itn.verbalizers.verbalize import VerbalizeFst

    return SentenceVerbalizeFst(VerbalizeFst(), itn_verbalizers.WordFst())


REGISTRY: dict[tuple[str, Direction], GrammarFactory] = {
    ("ta", TN): GrammarFactory(_ta_tn_classify, _ta_tn_verbalize),
    ("ta", ITN): GrammarFactory(_ta_itn_classify, _ta_itn_verbalize),
    ("te", TN): GrammarFactory(_te_tn_classify, _te_tn_verbalize),
    ("te", ITN): GrammarFactory(_te_itn_classify, _te_itn_verbalize),
    ("ml", TN): GrammarFactory(_ml_tn_classify, _ml_tn_verbalize),
    ("ml", ITN): GrammarFactory(_ml_itn_classify, _ml_itn_verbalize),
    ("kn", TN): GrammarFactory(_kn_tn_classify, _kn_tn_verbalize),
    ("kn", ITN): GrammarFactory(_kn_itn_classify, _kn_itn_verbalize),
}


def supported_languages(direction: Direction) -> list[str]:
    """
    Return the language codes registered for the given direction.
    """
    return sorted(lang for lang, d in REGISTRY if d == direction)
