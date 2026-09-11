"""
Unit tests for the Hindi measure grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestMeasure:
    """
    Golden-file tests for the measure semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("hi", "tn", "measure"))
    def test_tn(self, hi_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert hi_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("hi", "itn", "measure"))
    def test_itn(self, hi_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert hi_itn.inverse_normalize(text) in expected
