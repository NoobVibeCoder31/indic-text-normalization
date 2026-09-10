"""
Integrity checks for the packaged TSV mapping tables of every registered language.
"""

import re
import unicodedata
from pathlib import Path

import pytest

from indic_text_normalization.core.registry import REGISTRY

SRC_ROOT = Path(__file__).parent.parent / "src" / "indic_text_normalization"
LANGUAGES = sorted({lang for lang, _ in REGISTRY})
TSV_FILES = sorted(p for lang in LANGUAGES for p in (SRC_ROOT / lang / "data").rglob("*.tsv"))

# Tables kept for provenance or benchmarks that no grammar reads.
KNOWN_UNUSED = {
    "ta/data/digits.tsv",
    "ta/data/numbers/thousands.tsv",
    "ta/data/ordinal/exceptions.tsv",
    "ta/data/ordinal/suffixes.tsv",
    "ta/data/ordinal/suffixes_map.tsv",
    "ta/data/telephone/landline_context.tsv",
    "ta/data/telephone/mobile_context.tsv",
}


def _rel(path: Path) -> str:
    return str(path.relative_to(SRC_ROOT))


def _data_rel(path: Path) -> str:
    """Path below ``<lang>/data/`` (the form grammars pass to ``data_path``)."""
    return str(path.relative_to(SRC_ROOT / path.relative_to(SRC_ROOT).parts[0] / "data"))


class TestDataIntegrity:
    """
    Every packaged TSV must be NFC-normalized, well-formed, referenced and documented.
    """

    @pytest.mark.parametrize("path", TSV_FILES, ids=_rel)
    def test_nfc(self, path: Path) -> None:
        """
        File content is NFC-normalized.
        """
        text = path.read_text(encoding="utf-8")
        assert unicodedata.normalize("NFC", text) == text

    @pytest.mark.parametrize("path", TSV_FILES, ids=_rel)
    def test_rows_well_formed(self, path: Path) -> None:
        """
        Non-empty rows have one to three tab-separated columns without stray whitespace
        or U+00A0 NO-BREAK SPACE.
        """
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            cols = line.split("\t")
            assert 1 <= len(cols) <= 3, f"bad column count in {path.name}: {line!r}"
            for col in cols:
                assert col == col.strip(), f"stray whitespace in {path.name}: {line!r}"
                assert " " not in col, f"U+00A0 in {path.name}: {line!r}"

    @pytest.mark.parametrize("path", TSV_FILES, ids=_rel)
    def test_referenced_by_a_grammar(self, path: Path) -> None:
        """
        Every table is read by a grammar of its language or a shared core grammar, or is
        listed as known unused.
        """
        if _rel(path) in KNOWN_UNUSED:
            pytest.skip("documented unused table")
        lang_dir = SRC_ROOT / path.relative_to(SRC_ROOT).parts[0]
        needle = _data_rel(path)
        sources = [
            p.read_text(encoding="utf-8")
            for root in (lang_dir, SRC_ROOT / "core")
            for p in root.rglob("*.py")
        ]
        assert any(needle in src for src in sources), f"{needle} is read by no grammar"

    @pytest.mark.parametrize("path", TSV_FILES, ids=_rel)
    def test_documented_in_readme(self, path: Path) -> None:
        """
        Every table has a provenance row (or a glob covering it) in the language data README.
        """
        lang_dir = SRC_ROOT / path.relative_to(SRC_ROOT).parts[0]
        readme = (lang_dir / "data" / "README.md").read_text(encoding="utf-8")
        rel = _data_rel(path)
        stem = rel.rsplit("/", 1)[-1].removesuffix(".tsv")
        folder = rel.rsplit("/", 1)[0] if "/" in rel else ""
        assert (
            f"`{rel}`" in readme
            or (folder and f"`{folder}/*.tsv`" in readme)
            or (
                folder
                and re.search(
                    rf"`{re.escape(folder)}/\{{[^}}]*\b{re.escape(stem)}\b[^}}]*\}}\.tsv`", readme
                )
            )
        ), f"{rel} is not documented in {lang_dir.name}/data/README.md"

    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_no_sixty_in_clock_tables(self, lang: str) -> None:
        """
        Minute and second tables stop at 59 so 10:60 is never a time.
        """
        for name in ("minutes", "seconds"):
            path = SRC_ROOT / lang / "data" / "time" / f"{name}.tsv"
            keys = [
                line.split("\t")[0]
                for line in path.read_text(encoding="utf-8").splitlines()
                if line
            ]
            digits = {unicodedata.digit(c) for key in keys for c in key}
            values = [int("".join(str(unicodedata.digit(c)) for c in key)) for key in keys]
            assert digits <= set(range(10))
            assert max(values) == 59
            assert 60 not in values

    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_no_english_ordinal_units(self, lang: str) -> None:
        """
        The unit table never contains st/nd/rd/th, which would swallow English ordinals.
        """
        path = SRC_ROOT / lang / "data" / "measure" / "unit.tsv"
        keys = {
            line.split("\t")[0] for line in path.read_text(encoding="utf-8").splitlines() if line
        }
        assert not keys & {"st", "nd", "rd", "th"}

    def test_files_exist(self) -> None:
        """
        The data tree is non-trivial for every language.
        """
        for lang in LANGUAGES:
            assert len([p for p in TSV_FILES if _rel(p).startswith(f"{lang}/")]) > 15


class TestMoneyTablePairing:
    """
    Every minor unit TN can emit must invert to its own major currency's symbol.
    """

    def _rows(self, lang: str, name: str) -> list[list[str]]:
        path = SRC_ROOT / lang / "data" / "money" / name
        if not path.exists():
            return []
        return [
            line.split("\t")
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_every_major_minor_pair_is_invertible(self, lang: str) -> None:
        """
        Each major/minor pair resolves to a symbol, so ITN can pair the two words.
        """
        symbol_of = dict(self._rows(lang, "currency_itn.tsv"))
        missing = [
            (major, minor)
            for major, minor in self._rows(lang, "major_minor_currencies.tsv")
            if major not in symbol_of
        ]
        assert not missing, f"{lang}: majors with no ITN symbol: {missing}"

    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_extras_table_adds_no_derivable_row(self, lang: str) -> None:
        """
        An extras table holds only what the major/minor pairing cannot supply.
        """
        symbol_of = dict(self._rows(lang, "currency_itn.tsv"))
        derived = {
            (minor, symbol_of[major])
            for major, minor in self._rows(lang, "major_minor_currencies.tsv")
            if major in symbol_of
        }
        redundant = [row for row in self._rows(lang, "minor_unit_itn.tsv") if tuple(row) in derived]
        assert not redundant, f"{lang}: derivable rows in the extras table: {redundant}"
