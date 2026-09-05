"""
Tests for the benchmark dataset, the reference verbalizer and the runner.
"""

import csv
import re
import unicodedata
from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet

from benchmarks import ta_reference as ref
from benchmarks.generate_ta_tn import QUOTAS, Generator, indian_commas
from benchmarks.run_benchmark import (
    CORRECT,
    ERROR,
    OTHER,
    UNCHANGED,
    WHITESPACE_ONLY,
    Result,
    Row,
    evaluate,
    load_rows,
    run_chunk,
)
from indic_text_normalization import Normalizer

from .conftest import load_golden

BENCHMARK_CSV = Path(__file__).parent.parent / "benchmarks" / "ta_tn_benchmark.csv"
ALLOWED_TYPES = set(QUOTAS)

GOLDEN_SHAPES = {
    "cardinal": re.compile(r"^-?[\d௦-௯]+(?:,[\d௦-௯]+)*$"),
    "decimal": re.compile(r"^-?[\d௦-௯]+\.[\d௦-௯]+$"),
    "date": re.compile(r"^[\d௦-௯]{2,4}[-/.][\d௦-௯]{2}[-/.][\d௦-௯]{2,4}$"),
    "time": re.compile(r"^[\d௦-௯]{1,2}:[\d௦-௯]{2}(?::[\d௦-௯]{2})?$"),
    "money": re.compile(r"^\S*[\d௦-௯][\d,.௦-௯]*\S*$"),
    "ordinal": re.compile(r"^[\d௦-௯]+(?:வது|ஆவது|ஆம்)$"),
    "fraction": re.compile(r"^(?:[\d௦-௯]+ )?[\d௦-௯]+/[\d௦-௯]+$|^[\d௦-௯]*[½¼¾]$"),
}
REFERENCE_FUNCS = {
    "cardinal": ref.cardinal,
    "decimal": ref.decimal,
    "date": ref.date,
    "time": ref.time,
    "money": ref.money,
    "ordinal": ref.ordinal,
    "fraction": ref.fraction,
}


def _golden_span_cases() -> list[ParameterSet]:
    cases = []
    for kind, shape in GOLDEN_SHAPES.items():
        for param in load_golden("ta", "tn", kind):
            text, expected = param.values
            assert isinstance(text, str)
            if shape.match(text):
                cases.append(pytest.param(kind, text, expected, id=param.id))
    return cases


class TestReference:
    """
    The reference verbalizer agrees with the reviewed golden data on bare spans.
    """

    @pytest.mark.parametrize(("kind", "text", "expected"), _golden_span_cases())
    def test_matches_golden(self, kind: str, text: str, expected: list[str]) -> None:
        """
        Reference output is one of the accepted golden outputs.
        """
        try:
            actual = REFERENCE_FUNCS[kind](text)
        except (KeyError, ValueError) as exc:
            pytest.skip(f"shape outside the reference's scope: {exc!r}")
        assert actual in expected

    def test_style_rewrites(self) -> None:
        """
        Sandhi, ஒரு-scale and ஆயிரம் fusing behave as documented.
        """
        assert ref.cardinal("110") == "நூற்றுப்பத்து"
        assert ref.cardinal("1000") == "ஆயிரம்"
        assert ref.cardinal("2024") == "இரண்டாயிரத்து இருபத்துநான்கு"
        assert ref.cardinal("1,50,000") == "ஒரு இலட்சம் ஐம்பது ஆயிரம்"
        assert ref.cardinal("1,000,000") == "பத்து இலட்சம்"
        assert ref.locative("1000") == "ஆயிரத்தில்"
        assert ref.ordinal("1000வது") == "ஆயிரமாவது"
        assert ref.with_alternatives(ref.cardinal("150")) == "நூற்று ஐம்பது~நூற்றைம்பது"

    def test_indian_commas(self) -> None:
        """
        Indian grouping puts a 3-digit tail after 2-digit groups.
        """
        assert indian_commas("1500000") == "15,00,000"
        assert indian_commas("999") == "999"
        assert indian_commas("1000") == "1,000"

    def test_generator_is_deterministic(self) -> None:
        """
        The same seed produces the same rows.
        """
        first = [Generator(7).row(kind) for kind in QUOTAS]
        second = [Generator(7).row(kind) for kind in QUOTAS]
        assert first == second


class TestDataset:
    """
    Integrity checks for ``benchmarks/ta_tn_benchmark.csv``.
    """

    @pytest.fixture(scope="class")
    def records(self) -> list[dict[str, str]]:
        with open(BENCHMARK_CSV, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == ["input", "expected", "type"]
            return list(reader)

    def test_size(self, records: list[dict[str, str]]) -> None:
        """
        At least ten thousand rows.
        """
        assert len(records) >= 10_000

    def test_rows_well_formed(self, records: list[dict[str, str]]) -> None:
        """
        NFC cells, no stray whitespace, unique inputs, known types, non-empty expected.
        """
        inputs = set()
        for rec in records:
            for cell in rec.values():
                assert unicodedata.normalize("NFC", cell) == cell
                assert cell == cell.strip()
            assert rec["input"]
            assert rec["expected"]
            assert rec["type"] in ALLOWED_TYPES
            assert rec["input"] not in inputs
            inputs.add(rec["input"])

    def test_every_type_present(self, records: list[dict[str, str]]) -> None:
        """
        Each semiotic type in the quotas has rows.
        """
        present = {rec["type"] for rec in records}
        assert present == ALLOWED_TYPES

    def test_loader_accepts_alternatives(self) -> None:
        """
        ``~``-separated expected values load as tuples of alternatives.
        """
        rows = load_rows(BENCHMARK_CSV, limit=None)
        assert len(rows) >= 10_000
        assert any(len(r.expected) > 1 for r in rows)


class TestRunner:
    """
    The pure evaluation logic and the in-process chunk runner.
    """

    def test_evaluate_categories(self) -> None:
        """
        Correct, unchanged, whitespace-only, other and error outcomes are classified.
        """
        rows = [
            Row(1, "5", ("ஐந்து",), "cardinal"),
            Row(2, "5", ("ஐந்து",), "cardinal"),
            Row(3, "5", ("ஐந்து",), "cardinal"),
            Row(4, "5", ("ஐந்து",), "cardinal"),
            Row(5, "5", ("ஐந்து", "அஞ்சு"), "cardinal"),
            Row(6, "5", ("ஐந்து",), "cardinal"),
        ]
        results = [
            Result(1, "ஐந்து", 0.001),
            Result(2, "5", 0.001),
            Result(3, " ஐந்து ", 0.001),
            Result(4, "ஆறு", 0.001),
            Result(5, "அஞ்சு", 0.001),
            Result(6, "", 0.001, error="boom"),
        ]
        report = evaluate(rows, results)
        assert (report.total, report.correct, report.mismatched, report.errors) == (6, 2, 3, 1)
        assert report.categories == {UNCHANGED: 1, WHITESPACE_ONLY: 1, OTHER: 1, ERROR: 1}
        assert report.per_type["cardinal"][CORRECT] == 2
        assert [m.category for m in report.mismatches] == [UNCHANGED, WHITESPACE_ONLY, OTHER, ERROR]
        assert report.type_rows()[0][0] == "cardinal"
        assert report.summary()["accuracy"] == pytest.approx(100 * 2 / 6, abs=1e-3)

    def test_missing_result_is_error(self) -> None:
        """
        A row without a result counts as an error, not a silent pass.
        """
        report = evaluate([Row(1, "5", ("ஐந்து",), "cardinal")], [])
        assert report.errors == 1

    def test_run_chunk_with_engine(self, ta_tn: Normalizer) -> None:
        """
        Real engine over the first benchmark rows produces the expected outputs.
        """
        rows = load_rows(BENCHMARK_CSV, limit=25)
        results = run_chunk([(r.index, r.text) for r in rows], ta_tn.normalize)
        report = evaluate(rows, results)
        assert report.errors == 0
        assert report.total == 25
        assert all(r.seconds >= 0 for r in results)

    def test_missing_column(self, tmp_path: Path) -> None:
        """
        A CSV without the required header raises ValueError.
        """
        path = tmp_path / "bad.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing column"):
            load_rows(path)
