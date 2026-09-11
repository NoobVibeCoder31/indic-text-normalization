"""
Unit tests for the Malayalam cardinal grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestCardinal:
    """
    Golden-file tests for the cardinal semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("ml", "tn", "cardinal"))
    def test_tn(self, ml_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert ml_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("ml", "itn", "cardinal"))
    def test_itn(self, ml_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert ml_itn.inverse_normalize(text) in expected
