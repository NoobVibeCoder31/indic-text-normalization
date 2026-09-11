"""
Unit tests for the Telugu fraction grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestFraction:
    """
    Golden-file tests for the fraction semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("te", "tn", "fraction"))
    def test_tn(self, te_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert te_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("te", "itn", "fraction"))
    def test_itn(self, te_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert te_itn.inverse_normalize(text) in expected
