"""
Tests for the sentence-level tokenizer shared by every language.
"""

import pynini
import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from .conftest import DATA_DIR


def _golden_inputs(lang: str, direction: str) -> list[str]:
    inputs = []
    for path in sorted((DATA_DIR / lang / direction).glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                inputs.append(line.split("~")[0])
    return inputs


@pytest.mark.parametrize("lang", ["ta", "te"])
class TestPrePass:
    """
    The TN spacing pre-pass is a function of the text, composed at call time.
    """

    def test_tn_has_a_pre_pass_and_itn_none(
        self, lang: str, request: pytest.FixtureRequest
    ) -> None:
        """
        Only the TN tokenizer rewrites spacing before tagging.
        """
        tn: Normalizer = request.getfixturevalue(f"{lang}_tn")
        itn: InverseNormalizer = request.getfixturevalue(f"{lang}_itn")
        assert tn._engine.pre_pass is not None
        assert itn._engine.pre_pass is None

    def test_pre_pass_is_functional_on_golden_inputs(
        self, lang: str, request: pytest.FixtureRequest
    ) -> None:
        """
        Every golden TN input has exactly one rewrite, so tagging sees one string.
        """
        tn: Normalizer = request.getfixturevalue(f"{lang}_tn")
        pre_pass = tn._engine.pre_pass
        assert pre_pass is not None
        ambiguous = []
        for text in _golden_inputs(lang, "tn"):
            outputs = list((pynini.escape(text) @ pre_pass).paths().ostrings())
            if len(outputs) != 1:
                ambiguous.append((text, outputs[:3]))
        assert ambiguous == []
