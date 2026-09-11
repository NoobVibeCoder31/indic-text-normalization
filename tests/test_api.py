"""
Unit tests for the public API and grammar registry.
"""

from pathlib import Path

import pytest

import indic_text_normalization
from indic_text_normalization import InverseNormalizer, Normalizer, api
from indic_text_normalization.core import cache
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

    @pytest.mark.parametrize("lang", ["ta", "te", "ml", "kn", "hi"])
    def test_registry_lists_language(self, lang: str) -> None:
        """
        Every shipped language is registered for both directions.
        """
        assert lang in supported_languages(TN)
        assert lang in supported_languages(ITN)

    def test_empty_input_telugu(self, te_tn: Normalizer, te_itn: InverseNormalizer) -> None:
        """
        Empty and whitespace-only inputs come back empty for Telugu too.
        """
        assert te_tn.normalize("") == ""
        assert te_tn.normalize(" \t ") == ""
        assert te_itn.inverse_normalize("   ") == ""

    @pytest.mark.parametrize("lang", ["ta", "te", "ml", "kn", "hi"])
    def test_far_cache_round_trip(
        self,
        tmp_path: Path,
        lang: str,
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        A grammar saved to FAR loads back and produces identical output.

        The session normalizer's compiled FSTs are written to the cache instead of
        compiling a second time, so this exercises the load path in seconds.
        """
        live: Normalizer = request.getfixturevalue(f"{lang}_tn")
        engine = live._engine
        grammar = cache.Grammar(engine.classify, engine.verbalize, engine.pre_pass)
        cache.save(cache.far_path(tmp_path, lang, TN), grammar)
        # A failed load would silently recompile, so compiling is made impossible here.
        monkeypatch.setattr(api, "_compile", lambda _factory: pytest.fail("cache miss"))
        reloaded = Normalizer(lang=lang, cache_dir=str(tmp_path))
        assert (reloaded._engine.pre_pass is None) == (engine.pre_pass is None)
        for text in ["123", "₹50", "10:30", "5%కి", "+91 9876543210", "5+3=8"]:
            assert reloaded.normalize(text) == live.normalize(text)


class TestGrammarCacheIdentity:
    """
    The FAR cache is keyed by the grammar sources, not just the language and direction.
    """

    def test_path_includes_the_digest(self, tmp_path: Path) -> None:
        """
        The FAR path is nested under a digest, so two grammar versions cannot collide.
        """
        path = cache.far_path(tmp_path, "ta", "itn")
        assert path.name == "ta_itn.far"
        assert path.parent.name == cache.grammar_digest("ta")

    def test_digest_changes_when_a_data_file_changes(self) -> None:
        """
        Editing a packaged table invalidates the cache identity, so a stale FAR written
        before the edit is never reused.
        """
        table = (
            Path(indic_text_normalization.__file__).resolve().parent
            / "ta"
            / "data"
            / "numbers"
            / "zero.tsv"
        )
        original = table.read_bytes()
        before = cache.grammar_digest("ta")
        try:
            table.write_bytes(original + b"\n")
            cache.grammar_digest.cache_clear()
            after = cache.grammar_digest("ta")
        finally:
            table.write_bytes(original)
            cache.grammar_digest.cache_clear()
        assert after != before
        assert cache.grammar_digest("ta") == before


class TestConvenienceHelpers:
    """
    The module-level helpers reuse one grammar per language instead of rebuilding.
    """

    def test_grammar_is_built_once_per_language(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Repeated calls share a normalizer, so a caller does not pay the build each time.
        """
        builds: list[str] = []

        class _StubNormalizer:
            def __init__(self, lang: str) -> None:
                builds.append(lang)

            def normalize(self, text: str) -> str:
                return text.upper()

        monkeypatch.setattr(api, "Normalizer", _StubNormalizer)
        api._normalizer.cache_clear()
        try:
            assert api.normalize("a", lang="xx") == "A"
            assert api.normalize("b", lang="xx") == "B"
            assert api.normalize("c", lang="yy") == "C"
        finally:
            api._normalizer.cache_clear()
        assert builds == ["xx", "yy"]
