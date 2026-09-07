"""
Explicit grammar registry mapping ``(lang, direction)`` to grammar factories.
"""

from collections.abc import Callable
from typing import NamedTuple

from indic_text_normalization.core.graph_utils import GraphFst

Direction = str

TN = "tn"
ITN = "itn"


class GrammarFactory(NamedTuple):
    """
    Factory pair building the classify and verbalize grammars for one language/direction.
    """

    classify: Callable[[], GraphFst]
    verbalize: Callable[[], GraphFst]


def _ta_tn_classify() -> GraphFst:
    from indic_text_normalization.ta.tn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _ta_tn_verbalize() -> GraphFst:
    from indic_text_normalization.ta.tn.verbalizers.verbalize_final import VerbalizeFinalFst

    return VerbalizeFinalFst()


def _ta_itn_classify() -> GraphFst:
    from indic_text_normalization.ta.itn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _ta_itn_verbalize() -> GraphFst:
    from indic_text_normalization.ta.itn.verbalizers.verbalize_final import VerbalizeFinalFst

    return VerbalizeFinalFst()


def _te_tn_classify() -> GraphFst:
    from indic_text_normalization.te.tn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _te_tn_verbalize() -> GraphFst:
    from indic_text_normalization.te.tn.verbalizers.verbalize_final import VerbalizeFinalFst

    return VerbalizeFinalFst()


def _te_itn_classify() -> GraphFst:
    from indic_text_normalization.te.itn.taggers.tokenize_and_classify import ClassifyFst

    return ClassifyFst()


def _te_itn_verbalize() -> GraphFst:
    from indic_text_normalization.te.itn.verbalizers.verbalize_final import VerbalizeFinalFst

    return VerbalizeFinalFst()


REGISTRY: dict[tuple[str, Direction], GrammarFactory] = {
    ("ta", TN): GrammarFactory(_ta_tn_classify, _ta_tn_verbalize),
    ("ta", ITN): GrammarFactory(_ta_itn_classify, _ta_itn_verbalize),
    ("te", TN): GrammarFactory(_te_tn_classify, _te_tn_verbalize),
    ("te", ITN): GrammarFactory(_te_itn_classify, _te_itn_verbalize),
}


def supported_languages(direction: Direction) -> list[str]:
    """
    Return the language codes registered for the given direction.
    """
    return sorted(lang for lang, d in REGISTRY if d == direction)
