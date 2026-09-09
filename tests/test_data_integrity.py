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


class TestMoneyTablePairing:
    """
    Every minor unit TN can emit must invert to its own major currency's symbol.
    """

    def _rows(self, name: str) -> list[list[str]]:
        path = DATA_ROOT / "money" / name
        return [
            line.split("\t")
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_every_major_minor_pair_is_invertible(self) -> None:
        """
        Each major/minor pair resolves to a symbol, so ITN can pair the two words.
        """
        symbol_of = dict(self._rows("currency_itn.tsv"))
        missing = [
            (major, minor)
            for major, minor in self._rows("major_minor_currencies.tsv")
            if major not in symbol_of
        ]
        assert not missing, f"majors with no ITN symbol: {missing}"

    def test_extras_table_adds_no_derivable_row(self) -> None:
        """
        The extras table holds only what the major/minor pairing cannot supply.
        """
        symbol_of = dict(self._rows("currency_itn.tsv"))
        derived = {
            (minor, symbol_of[major])
            for major, minor in self._rows("major_minor_currencies.tsv")
            if major in symbol_of
        }
        redundant = [row for row in self._rows("minor_unit_itn.tsv") if tuple(row) in derived]
        assert not redundant, f"already derived from major_minor_currencies.tsv: {redundant}"
