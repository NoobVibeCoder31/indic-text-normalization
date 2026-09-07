"""
Shared fixtures and golden-file loading for the test suite.
"""

from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet

from indic_text_normalization import InverseNormalizer, Normalizer

DATA_DIR = Path(__file__).parent / "data"


def load_golden(lang: str, direction: str, name: str) -> list[ParameterSet]:
    """
    Load ``input~expected[~alt_expected...]`` cases from a golden data file.

    Parameters
    ----------
    lang : ``str``
        Language code, e.g. ``ta``.
    direction : ``str``
        Either ``tn`` or ``itn``.
    name : ``str``
        Semiotic class name, matching the data file stem.

    Returns
    -------
    ``list[ParameterSet]``
        One param per case: (input, accepted outputs), id ``<name>-<line>``.
    """
    path = DATA_DIR / lang / direction / f"{name}.txt"
    params = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("~")
            params.append(pytest.param(parts[0], parts[1:], id=f"{name}-{i:03d}"))
    return params


@pytest.fixture(scope="session")
def ta_tn() -> Normalizer:
    """
    Session-wide Tamil TN normalizer (grammar compiled once).
    """
    return Normalizer(lang="ta")


@pytest.fixture(scope="session")
def ta_itn() -> InverseNormalizer:
    """
    Session-wide Tamil ITN normalizer (grammar compiled once).
    """
    return InverseNormalizer(lang="ta")


@pytest.fixture(scope="session")
def te_tn() -> Normalizer:
    """
    Session-wide Telugu TN normalizer (grammar compiled once).
    """
    return Normalizer(lang="te")


@pytest.fixture(scope="session")
def te_itn() -> InverseNormalizer:
    """
    Session-wide Telugu ITN normalizer (grammar compiled once).
    """
    return InverseNormalizer(lang="te")
