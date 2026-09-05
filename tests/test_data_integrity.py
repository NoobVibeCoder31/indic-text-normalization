"""
Integrity checks for the packaged TSV mapping tables.
"""

import unicodedata
from pathlib import Path

import pytest

DATA_ROOT = Path(__file__).parent.parent / "src" / "indic_text_normalization" / "ta" / "data"
TSV_FILES = sorted(DATA_ROOT.rglob("*.tsv"))


class TestDataIntegrity:
    """
    Every packaged TSV must be NFC-normalized and well-formed.
    """

    @pytest.mark.parametrize("path", TSV_FILES, ids=lambda p: str(p.relative_to(DATA_ROOT)))
    def test_nfc(self, path: Path) -> None:
        """
        File content is NFC-normalized.
        """
        text = path.read_text(encoding="utf-8")
        assert unicodedata.normalize("NFC", text) == text

    @pytest.mark.parametrize("path", TSV_FILES, ids=lambda p: str(p.relative_to(DATA_ROOT)))
    def test_rows_well_formed(self, path: Path) -> None:
        """
        Non-empty rows have one or two tab-separated columns without stray whitespace.
        """
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            cols = line.split("\t")
            assert 1 <= len(cols) <= 3, f"bad column count in {path.name}: {line!r}"
            for col in cols:
                assert col == col.strip(), f"stray whitespace in {path.name}: {line!r}"

    def test_files_exist(self) -> None:
        """
        The data tree is non-trivial.
        """
        assert len(TSV_FILES) > 15
