"""
Data-file helpers shared by all language packages.
"""

import csv
from importlib import resources
from pathlib import Path

import pynini


def data_path(lang: str, *parts: str) -> str:
    """
    Return the absolute path of a data file inside a language package.

    Parameters
    ----------
    lang : ``str``
        Language code, e.g. ``ta``.
    parts : ``str``
        Path below ``<lang>/data/``, as one string (``numbers/digit.tsv``) or components.

    Returns
    -------
    ``str``
        Absolute filesystem path to the data file.
    """
    root = resources.files(f"indic_text_normalization.{lang}")
    return str(Path(str(root)) / "data" / Path(*parts))


def load_labels(path: str, *, min_fields: int = 1) -> list[list[str]]:
    """
    Load a tab-separated mapping file as a list of rows, skipping blank lines.

    Parameters
    ----------
    path : ``str``
        Absolute path to the data file.
    min_fields : ``int``, optional (default = 1)
        Minimum number of columns a row must have.

    Returns
    -------
    ``list[list[str]]``
        One list of column values per non-blank row.

    Raises
    ------
    ``ValueError``
        If a non-blank row has fewer than ``min_fields`` columns.
    """
    rows = []
    with open(path, encoding="utf-8") as f:
        for line_number, row in enumerate(csv.reader(f, delimiter="\t"), start=1):
            if not row or not row[0]:
                continue
            if len(row) < min_fields:
                raise ValueError(f"{path}:{line_number} has {len(row)} of {min_fields} columns")
            rows.append(row)
    return rows


def table_fst(path: str, *, key: int = 0, value: int = 1) -> pynini.Fst:
    """
    Compile two columns of a TSV table into an optimized string map.

    Unlike ``pynini.string_file`` this tolerates a third column that is not a weight, so
    it is the loader for the three-column tables (singular, plural, oblique).
    """
    width = max(key, value) + 1
    rows = load_labels(path, min_fields=width)
    return pynini.string_map([(row[key], row[value]) for row in rows]).optimize()
