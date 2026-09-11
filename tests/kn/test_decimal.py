"""
Unit tests for the Kannada decimal grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestDecimal:
    """
    Golden-file tests for the decimal semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("kn", "tn", "decimal"))
    def test_tn(self, kn_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert kn_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("kn", "itn", "decimal"))
    def test_itn(self, kn_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert kn_itn.inverse_normalize(text) in expected
