"""
Unit tests for the Kannada measure grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestMeasure:
    """
    Golden-file tests for the measure semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("kn", "tn", "measure"))
    def test_tn(self, kn_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert kn_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("kn", "itn", "measure"))
    def test_itn(self, kn_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert kn_itn.inverse_normalize(text) in expected
