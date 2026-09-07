"""
Tests for the benchmark datasets, the reference verbalizers and the runner.
"""

import csv
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest
from _pytest.mark.structures import ParameterSet

from benchmarks import generate_ta_tn, generate_te_tn
from benchmarks import ta_reference as ref
from benchmarks import te_reference
from benchmarks.generate_ta_tn import QUOTAS, indian_commas
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

BENCHMARKS = Path(__file__).parent.parent / "benchmarks"
BENCHMARK_CSV = BENCHMARKS / "ta_tn_benchmark.csv"
# The datasets are generated, not committed (2 MB each; CLAUDE.md requires discussion
# before committing test data over 1 MB). Regenerate with benchmarks/generate_<lang>_tn.py.
requires_benchmark = pytest.mark.skipif(
    not BENCHMARK_CSV.exists(), reason=f"{BENCHMARK_CSV.name} not generated"
)
ALLOWED_TYPES = set(QUOTAS)


def _shapes(digits: str, ordinal_suffix: str) -> dict[str, re.Pattern[str]]:
    d = rf"[\d{digits}]"
    return {
        "cardinal": re.compile(rf"^-?{d}+(?:,{d}+)*$"),
        "decimal": re.compile(rf"^-?{d}+\.{d}+$"),
        "date": re.compile(rf"^{d}{{2,4}}[-/.]{d}{{2}}[-/.]{d}{{2,4}}$"),
        "time": re.compile(rf"^{d}{{1,2}}:{d}{{2}}(?::{d}{{2}})?$"),
        "money": re.compile(rf"^\S*{d}[\d,.{digits}]*\S*$"),
        "ordinal": re.compile(rf"^{d}+(?:{ordinal_suffix})$"),
        "fraction": re.compile(rf"^(?:{d}+ )?{d}+/{d}+$|^{d}*[½¼¾]$"),
    }


@dataclass(frozen=True)
class Language:
    """
    One benchmarked language: its reference module, generator module and dataset.
    """

    code: str
    reference: ModuleType
    generator: ModuleType
    csv: Path
    shapes: dict[str, re.Pattern[str]]
    has_alternatives: bool


LANGUAGES = [
    Language("ta", ref, generate_ta_tn, BENCHMARK_CSV, _shapes("௦-௯", "வது|ஆவது|ஆம்"), True),
    Language(
        "te",
        te_reference,
        generate_te_tn,
        BENCHMARKS / "te_tn_benchmark.csv",
        _shapes("౦-౯", "వ|వది|-వ"),
        False,
    ),
]
LANGUAGE_IDS = [lang.code for lang in LANGUAGES]


def _reference_funcs(module: ModuleType) -> dict[str, Callable[[str], str]]:
    return {
        kind: getattr(module, kind)
        for kind in ("cardinal", "decimal", "date", "time", "money", "ordinal", "fraction")
    }


def _golden_span_cases() -> list[ParameterSet]:
    cases = []
    for lang in LANGUAGES:
        for kind, shape in lang.shapes.items():
            for param in load_golden(lang.code, "tn", kind):
                text, expected = param.values
                assert isinstance(text, str)
                if shape.match(text):
                    cases.append(
                        pytest.param(lang, kind, text, expected, id=f"{lang.code}-{param.id}")
                    )
    return cases


class TestReference:
    """
    The reference verbalizer agrees with the reviewed golden data on bare spans.
    """

    @pytest.mark.parametrize(("lang", "kind", "text", "expected"), _golden_span_cases())
    def test_matches_golden(
        self, lang: Language, kind: str, text: str, expected: list[str]
    ) -> None:
        """
        Reference output is one of the accepted golden outputs.
        """
        try:
            actual = _reference_funcs(lang.reference)[kind](text)
        except (KeyError, ValueError) as exc:
            pytest.skip(f"shape outside the reference's scope: {exc!r}")
        assert actual in expected

    def test_telugu_morphology(self) -> None:
        """
        Plural/oblique scale words, ఒక, -ింట denominators and suffix sandhi behave as documented.
        """
        assert te_reference.cardinal("2024") == "రెండు వేల ఇరవై నాలుగు"
        assert te_reference.cardinal("2000") == "రెండు వేలు"
        assert te_reference.cardinal("1,50,000") == "లక్ష యాభై వేలు"
        assert te_reference.cardinal("1,000,000") == "పది లక్షలు"
        assert te_reference.year("1947") == "పందొమ్మిది వందల నలభై ఏడు"
        assert te_reference.suffixed("2000", "లో") == "రెండు వేలలో"
        assert te_reference.suffixed("2000", "గా") == "రెండు వేలుగా"
        assert te_reference.money("₹2000") == "రెండు వేల రూపాయలు"
        assert te_reference.fraction("3/4") == "నాలుగింట మూడు వంతులు"
        assert te_reference.ordinal("20వ") == "ఇరవయ్యవ"
        assert te_reference.time("10:01 గంటలకి") == "పది గంటల ఒక నిమిషానికి"

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

    @pytest.mark.parametrize("lang", LANGUAGES, ids=LANGUAGE_IDS)
    def test_generator_is_deterministic(self, lang: Language) -> None:
        """
        The same seed produces the same rows.
        """
        gen = lang.generator.Generator
        first = [gen(7).row(kind) for kind in lang.generator.QUOTAS]
        second = [gen(7).row(kind) for kind in lang.generator.QUOTAS]
        assert first == second


@requires_benchmark
class TestDataset:
    """
    Integrity checks for the ``benchmarks/<lang>_tn_benchmark.csv`` datasets.
    """

    @pytest.fixture(scope="class", params=LANGUAGES, ids=LANGUAGE_IDS)
    def lang(self, request: pytest.FixtureRequest) -> Language:
        language: Language = request.param
        return language

    @pytest.fixture(scope="class")
    def records(self, lang: Language) -> list[dict[str, str]]:
        with open(lang.csv, encoding="utf-8", newline="") as f:
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

    def test_loader_accepts_alternatives(self, lang: Language) -> None:
        """
        ``~``-separated expected values load as tuples of alternatives.
        """
        rows = load_rows(lang.csv, limit=None)
        assert len(rows) >= 10_000
        assert any(len(r.expected) > 1 for r in rows) == lang.has_alternatives


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

    @requires_benchmark
    @pytest.mark.parametrize("lang", LANGUAGES, ids=LANGUAGE_IDS)
    def test_run_chunk_with_engine(self, lang: Language, request: pytest.FixtureRequest) -> None:
        """
        Real engine over the first benchmark rows produces the expected outputs.
        """
        normalizer: Normalizer = request.getfixturevalue(f"{lang.code}_tn")
        rows = load_rows(lang.csv, limit=25)
        results = run_chunk([(r.index, r.text) for r in rows], normalizer.normalize)
        report = evaluate(rows, results)
        assert report.errors == 0
        assert report.total == 25
        assert report.correct == 25
        assert all(r.seconds >= 0 for r in results)

    def test_missing_column(self, tmp_path: Path) -> None:
        """
        A CSV without the required header raises ValueError.
        """
        path = tmp_path / "bad.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing column"):
            load_rows(path)
