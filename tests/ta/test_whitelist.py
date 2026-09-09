"""
Unit tests for the Tamil whitelist grammars (TN and ITN).
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer

from ..conftest import load_golden


class TestWhitelist:
    """
    Golden-file tests for the whitelist semiotic class.
    """

    @pytest.mark.parametrize(("text", "expected"), load_golden("ta", "tn", "whitelist"))
    def test_tn(self, ta_tn: Normalizer, text: str, expected: list[str]) -> None:
        """
        The written form verbalizes to one of the accepted spoken forms.
        """
        assert ta_tn.normalize(text) in expected

    @pytest.mark.parametrize(("text", "expected"), load_golden("ta", "itn", "whitelist"))
    def test_itn(self, ta_itn: InverseNormalizer, text: str, expected: list[str]) -> None:
        """
        The spoken form inverse-normalizes to one of the accepted written forms.
        """
        assert ta_itn.inverse_normalize(text) in expected
