"""
Unit tests for the public API and grammar registry.
"""

import pytest

from indic_text_normalization import InverseNormalizer, Normalizer
from indic_text_normalization.core.registry import ITN, TN, supported_languages


class TestNormalizer:
    """
    Behavioral tests for Normalizer and InverseNormalizer entry points.
    """

    def test_unknown_language_raises(self) -> None:
        """
        An unregistered language raises ValueError for both directions.
        """
        with pytest.raises(ValueError, match="not supported"):
            Normalizer(lang="xx")
        with pytest.raises(ValueError, match="not supported"):
            InverseNormalizer(lang="xx")

    def test_empty_input(self, ta_tn: Normalizer) -> None:
        """
        Empty and whitespace-only inputs come back empty.
        """
        assert ta_tn.normalize("") == ""
        assert ta_tn.normalize("   ") == ""

    def test_empty_input_itn(self, ta_itn: InverseNormalizer) -> None:
        """
        Empty and whitespace-only inputs come back empty for ITN too.
        """
        assert ta_itn.inverse_normalize("") == ""
        assert ta_itn.inverse_normalize(" \t ") == ""

    def test_registry_lists_tamil(self) -> None:
        """
        Tamil is registered for both directions.
        """
        assert "ta" in supported_languages(TN)
        assert "ta" in supported_languages(ITN)

    def test_far_cache_round_trip(self, tmp_path: object, ta_tn: Normalizer) -> None:
        """
        A cached grammar loads from FAR and produces identical output.
        """
        cached = Normalizer(lang="ta", cache_dir=str(tmp_path))
        reloaded = Normalizer(lang="ta", cache_dir=str(tmp_path))
        for text in ["123", "₹50", "10:30"]:
            assert cached.normalize(text) == ta_tn.normalize(text)
            assert reloaded.normalize(text) == ta_tn.normalize(text)
