"""
Unit tests for the Hindi time grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestTime:
    """
    Golden-file tests for the time semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("hi", "tn", "time"))
    def test_tn(self, hi_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert hi_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("hi", "itn", "time"))
    def test_itn(self, hi_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert hi_itn.inverse_normalize(text) in expected
