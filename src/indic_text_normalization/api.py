"""
Public entry points: Normalizer (TN) and InverseNormalizer (ITN).
"""

from functools import cache as _memoize
from pathlib import Path

from indic_text_normalization.core import cache
from indic_text_normalization.core.engine import NormalizationEngine
from indic_text_normalization.core.registry import ITN, REGISTRY, TN, supported_languages


def _build_engine(
    lang: str,
    direction: str,
    cache_dir: str | Path | None,
    overwrite_cache: bool,
) -> NormalizationEngine:
    """
    Build (or load from FAR cache) the engine for a language/direction pair.

    Raises
    ------
    ``ValueError``
        If the language is not registered for the direction.
    """
    factory = REGISTRY.get((lang, direction))
    if factory is None:
        supported = ", ".join(supported_languages(direction))
        raise ValueError(
            f"Language {lang!r} is not supported for {direction}; supported: {supported}."
        )

    if cache_dir is not None:
        path = cache.far_path(cache_dir, lang, direction)
        if not overwrite_cache:
            cached = cache.load(path)
            if cached is not None:
                return NormalizationEngine(*cached)
        classify = factory.classify().fst
        verbalize = factory.verbalize().fst
        cache.save(path, classify, verbalize)
        return NormalizationEngine(classify, verbalize)

    return NormalizationEngine(factory.classify().fst, factory.verbalize().fst)


class Normalizer:
    """
    Text normalizer converting written form to spoken form, e.g. ௧௨ -> பன்னிரண்டு.

    Attributes
    ----------
    lang : ``str``, optional (default = "ta")
        Language code of the grammar to load.
    cache_dir : ``str | Path | None``, optional (default = None)
        Directory for compiled FAR grammar files; None disables caching.
    overwrite_cache : ``bool``, optional (default = False)
        If True, recompile grammars and overwrite an existing FAR file.
    """

    def __init__(
        self,
        lang: str = "ta",
        *,
        cache_dir: str | Path | None = None,
        overwrite_cache: bool = False,
    ) -> None:
        self.lang = lang
        self._engine = _build_engine(lang, TN, cache_dir, overwrite_cache)

    def normalize(self, text: str) -> str:
        """
        Return the spoken form of ``text``; unprocessable input is returned unchanged.
        """
        return self._engine.normalize(text)


class InverseNormalizer:
    """
    Inverse normalizer converting spoken form to written form, e.g. பன்னிரண்டு -> 12.

    Attributes
    ----------
    lang : ``str``, optional (default = "ta")
        Language code of the grammar to load.
    cache_dir : ``str | Path | None``, optional (default = None)
        Directory for compiled FAR grammar files; None disables caching.
    overwrite_cache : ``bool``, optional (default = False)
        If True, recompile grammars and overwrite an existing FAR file.
    """

    def __init__(
        self,
        lang: str = "ta",
        *,
        cache_dir: str | Path | None = None,
        overwrite_cache: bool = False,
    ) -> None:
        self.lang = lang
        self._engine = _build_engine(lang, ITN, cache_dir, overwrite_cache)

    def inverse_normalize(self, text: str) -> str:
        """
        Return the written form of ``text``; unprocessable input is returned unchanged.
        """
        return self._engine.normalize(text)


@_memoize
def _normalizer(lang: str) -> Normalizer:
    """
    Normalizer for ``lang``, built once per process.
    """
    return Normalizer(lang=lang)


@_memoize
def _inverse_normalizer(lang: str) -> InverseNormalizer:
    """
    InverseNormalizer for ``lang``, built once per process.
    """
    return InverseNormalizer(lang=lang)


def normalize(text: str, *, lang: str = "ta") -> str:
    """
    Normalize ``text`` to spoken form, reusing a grammar built once per language.

    The first call compiles the grammar, which takes minutes and several GB. Construct a
    :class:`Normalizer` with ``cache_dir`` instead to persist it across processes.
    """
    return _normalizer(lang).normalize(text)


def inverse_normalize(text: str, *, lang: str = "ta") -> str:
    """
    Inverse-normalize ``text`` to written form, reusing a grammar built once per language.

    The first call compiles the grammar, which takes minutes and several GB. Construct an
    :class:`InverseNormalizer` with ``cache_dir`` instead to persist it across processes.
    """
    return _inverse_normalizer(lang).inverse_normalize(text)
