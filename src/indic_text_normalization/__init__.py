"""
WFST-based text normalization and inverse text normalization for Indic languages.
"""

from indic_text_normalization.api import (
    InverseNormalizer,
    Normalizer,
    inverse_normalize,
    normalize,
)

__all__ = ["InverseNormalizer", "Normalizer", "inverse_normalize", "normalize"]
