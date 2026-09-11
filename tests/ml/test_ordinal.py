"""
Unit tests for the Malayalam ordinal grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestOrdinal:
    """
    Golden-file tests for the ordinal semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("ml", "tn", "ordinal"))
    def test_tn(self, ml_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert ml_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("ml", "itn", "ordinal"))
    def test_itn(self, ml_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert ml_itn.inverse_normalize(text) in expected
