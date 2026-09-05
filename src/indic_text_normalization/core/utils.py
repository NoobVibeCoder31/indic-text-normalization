"""
Data-file helpers shared by all language packages.
"""

import csv
from importlib import resources
from pathlib import Path


def data_path(lang: str, *parts: str) -> str:
    """
    Return the absolute path of a data file inside a language package.

    Parameters
    ----------
    lang : ``str``
        Language code, e.g. ``ta``.
    parts : ``str``
        Path components below ``<lang>/data/``.

    Returns
    -------
    ``str``
        Absolute filesystem path to the data file.
    """
    root = resources.files(f"indic_text_normalization.{lang}")
    return str(Path(str(root)) / "data" / Path(*parts))


def load_labels(path: str) -> list[list[str]]:
    """
    Load a tab-separated mapping file as a list of rows.
    """
    with open(path, encoding="utf-8") as f:
        return list(csv.reader(f, delimiter="\t"))
