"""
Run a normalizer over a benchmark CSV in parallel and report accuracy.

The CSV needs the columns ``input``, ``expected`` and ``type``. ``expected`` may hold
several accepted outputs separated by ``~`` (the golden-file convention).

Example::

    uv run python benchmarks/run_benchmark.py benchmarks/ta_tn_benchmark.csv --workers 8
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing
import statistics
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from indic_text_normalization import InverseNormalizer, Normalizer

ALTERNATIVE_SEPARATOR = "~"
CORRECT = "correct"
UNCHANGED = "unchanged"
WHITESPACE_ONLY = "whitespace_only"
OTHER = "other"
ERROR = "error"
MISMATCH_CATEGORIES = (UNCHANGED, WHITESPACE_ONLY, OTHER, ERROR)

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / ".far_cache"
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"

NormalizeFn = Callable[[str], str]


@dataclass(frozen=True)
class Row:
    """
    One benchmark row: index in the CSV, input text, accepted outputs, semiotic type.
    """

    index: int
    text: str
    expected: tuple[str, ...]
    kind: str


@dataclass(frozen=True)
class Result:
    """
    Normalizer output for one row, with wall time in seconds and an error message if any.
    """

    index: int
    actual: str
    seconds: float
    error: str | None = None


@dataclass(frozen=True)
class Mismatch:
    """
    A row whose output was not one of the accepted outputs.
    """

    index: int
    text: str
    expected: str
    actual: str
    kind: str
    category: str


@dataclass
class Report:
    """
    Aggregated benchmark outcome.
    """

    total: int = 0
    correct: int = 0
    mismatched: int = 0
    errors: int = 0
    per_type: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    categories: Counter[str] = field(default_factory=Counter)
    mismatches: list[Mismatch] = field(default_factory=list)
    latencies: list[float] = field(default_factory=list)
    slowest: list[tuple[float, str]] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return 100.0 * self.correct / self.total if self.total else 0.0

    def type_rows(self) -> list[tuple[str, int, int, float]]:
        """
        Per-type ``(type, rows, correct, accuracy)`` sorted worst first.
        """
        rows = []
        for kind, counter in self.per_type.items():
            n = sum(counter.values())
            ok = counter[CORRECT]
            rows.append((kind, n, ok, 100.0 * ok / n if n else 0.0))
        return sorted(rows, key=lambda r: (r[3], r[0]))

    def latency_ms(self) -> dict[str, float]:
        """
        p50/p95/max/mean per-row latency in milliseconds.
        """
        latencies = sorted(self.latencies)
        return {
            "p50": round(1000 * _quantile(latencies, 0.5), 3),
            "p95": round(1000 * _quantile(latencies, 0.95), 3),
            "max": round(1000 * latencies[-1], 3) if latencies else 0.0,
            "mean": round(1000 * statistics.fmean(latencies), 3) if latencies else 0.0,
        }

    def summary(self) -> dict[str, object]:
        return {
            "total": self.total,
            "correct": self.correct,
            "mismatched": self.mismatched,
            "errors": self.errors,
            "accuracy": round(self.accuracy, 4),
            "categories": dict(self.categories),
            "per_type": [
                {"type": k, "rows": n, "correct": ok, "accuracy": round(acc, 4)}
                for k, n, ok, acc in self.type_rows()
            ],
            "latency_ms": self.latency_ms(),
            "slowest": [{"ms": round(1000 * s, 3), "input": t} for s, t in self.slowest],
        }


def _quantile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    pos = min(len(sorted_values) - 1, max(0, round(q * (len(sorted_values) - 1))))
    return sorted_values[pos]


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


# ------------------------------------------------------------------------------ loading


def load_rows(
    path: Path,
    *,
    limit: int | None = None,
    input_col: str = "input",
    expected_col: str = "expected",
    type_col: str = "type",
) -> list[Row]:
    """
    Read benchmark rows from ``path``; raises ``ValueError`` on a missing column.
    """
    rows: list[Row] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in (input_col, expected_col, type_col) if c not in header]
        if missing:
            raise ValueError(f"{path}: missing column(s) {missing}; found {header}")
        for i, record in enumerate(reader, start=1):
            if limit is not None and len(rows) >= limit:
                break
            expected = tuple(_nfc(record[expected_col]).split(ALTERNATIVE_SEPARATOR))
            rows.append(Row(i, _nfc(record[input_col]), expected, record[type_col] or "unknown"))
    return rows


# ------------------------------------------------------------------------------ evaluation


def categorize(row: Row, result: Result) -> str:
    """
    Classify one result as correct or as a mismatch category.
    """
    if result.error is not None:
        return ERROR
    actual = _nfc(result.actual)
    if actual in row.expected:
        return CORRECT
    if actual == row.text:
        return UNCHANGED
    if any("".join(actual.split()) == "".join(e.split()) for e in row.expected):
        return WHITESPACE_ONLY
    return OTHER


def evaluate(rows: Iterable[Row], results: Iterable[Result], *, slowest: int = 5) -> Report:
    """
    Compare results with rows and aggregate a Report (pure, no I/O).
    """
    by_index = {r.index: r for r in results}
    report = Report()
    timings: list[tuple[float, str]] = []
    for row in rows:
        result = by_index.get(row.index)
        if result is None:
            result = Result(row.index, "", 0.0, error="no result returned")
        category = categorize(row, result)
        report.total += 1
        report.per_type[row.kind][category] += 1
        report.latencies.append(result.seconds)
        timings.append((result.seconds, row.text))
        if category == CORRECT:
            report.correct += 1
            continue
        report.categories[category] += 1
        if category == ERROR:
            report.errors += 1
        else:
            report.mismatched += 1
        report.mismatches.append(
            Mismatch(
                row.index,
                row.text,
                ALTERNATIVE_SEPARATOR.join(row.expected),
                result.actual if result.error is None else f"<error: {result.error}>",
                row.kind,
                category,
            )
        )
    report.slowest = sorted(timings, reverse=True)[:slowest]
    return report


# ------------------------------------------------------------------------------ execution

_NORMALIZE: NormalizeFn | None = None


def build_normalizer(lang: str, direction: str, cache_dir: Path | None) -> NormalizeFn:
    """
    Build (or load from FAR cache) the normalize callable for ``lang``/``direction``.
    """
    if direction == "tn":
        return Normalizer(lang=lang, cache_dir=cache_dir).normalize
    if direction == "itn":
        return InverseNormalizer(lang=lang, cache_dir=cache_dir).inverse_normalize
    raise ValueError(f"direction must be 'tn' or 'itn', got {direction!r}")


def _init_worker(lang: str, direction: str, cache_dir: str | None) -> None:
    global _NORMALIZE
    _NORMALIZE = build_normalizer(lang, direction, Path(cache_dir) if cache_dir else None)


def normalize_chunk(chunk: Sequence[tuple[int, str]]) -> list[Result]:
    """
    Normalize ``(index, text)`` pairs with the worker's engine.
    """
    if _NORMALIZE is None:
        raise RuntimeError("worker not initialised")
    return run_chunk(chunk, _NORMALIZE)


def run_chunk(chunk: Sequence[tuple[int, str]], normalize: NormalizeFn) -> list[Result]:
    """
    Normalize ``(index, text)`` pairs with ``normalize``, timing each call.
    """
    results = []
    for index, text in chunk:
        start = time.perf_counter()
        try:
            actual = normalize(text)
            results.append(Result(index, actual, time.perf_counter() - start))
        except Exception as exc:
            results.append(Result(index, "", time.perf_counter() - start, error=repr(exc)))
    return results


def _chunks(rows: Sequence[Row], size: int) -> list[list[tuple[int, str]]]:
    pairs = [(r.index, r.text) for r in rows]
    return [pairs[i : i + size] for i in range(0, len(pairs), size)]


def run(
    rows: Sequence[Row],
    *,
    workers: int,
    lang: str,
    direction: str,
    cache_dir: Path | None,
    chunk_size: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[Result]:
    """
    Normalize all rows with ``workers`` processes (in-process when ``workers == 1``).
    """
    if not rows:
        return []
    if chunk_size is None:
        chunk_size = max(1, min(500, -(-len(rows) // (max(workers, 1) * 8))))
    chunks = _chunks(rows, chunk_size)
    results: list[Result] = []
    done = 0
    if workers <= 1:
        normalize = build_normalizer(lang, direction, cache_dir)
        for chunk in chunks:
            results.extend(run_chunk(chunk, normalize))
            done += len(chunk)
            if progress:
                progress(done, len(rows))
        return results

    ctx = multiprocessing.get_context("spawn")
    cache_arg = str(cache_dir) if cache_dir else None
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=ctx,
        initializer=_init_worker,
        initargs=(lang, direction, cache_arg),
    ) as pool:
        for chunk_results in pool.map(normalize_chunk, chunks):
            results.extend(chunk_results)
            done += len(chunk_results)
            if progress:
                progress(done, len(rows))
    return results


# ------------------------------------------------------------------------------ reporting


def print_report(report: Report, *, show: int, elapsed: float, workers: int) -> None:
    """
    Print the console summary.
    """
    rate = report.total / elapsed if elapsed else 0.0
    print("=" * 72)
    print(
        f"rows: {report.total}   correct: {report.correct}   mismatched: {report.mismatched}   errors: {report.errors}"
    )
    print(
        f"accuracy: {report.accuracy:.2f}%   wall: {elapsed:.1f}s   throughput: {rate:.1f} rows/s   workers: {workers}"
    )
    lat = report.latency_ms()
    print(
        f"per-row latency ms: p50={lat['p50']}  p95={lat['p95']}  max={lat['max']}  mean={lat['mean']}"
    )
    print("-" * 72)
    print(f"{'type':<12}{'rows':>8}{'correct':>10}{'wrong':>8}{'accuracy':>10}")
    for kind, n, ok, acc in report.type_rows():
        print(f"{kind:<12}{n:>8}{ok:>10}{n - ok:>8}{acc:>9.2f}%")
    print("-" * 72)
    if report.categories:
        cats = "  ".join(
            f"{c}={report.categories[c]}" for c in MISMATCH_CATEGORIES if report.categories[c]
        )
        print(f"mismatch categories: {cats}")
    for m in report.mismatches[:show]:
        print(f"[{m.kind}/{m.category}] #{m.index}")
        print(f"  input:    {m.text}")
        print(f"  expected: {m.expected}")
        print(f"  actual:   {m.actual}")
    if len(report.mismatches) > show:
        print(f"... {len(report.mismatches) - show} more mismatches (see mismatches.csv)")
    if report.slowest:
        print("slowest rows:")
        for seconds, text in report.slowest:
            print(f"  {1000 * seconds:8.2f} ms  {text}")
    print("=" * 72)


def write_reports(
    report: Report,
    out_dir: Path,
    *,
    config: dict[str, object],
    elapsed: float,
    rows: Sequence[Row] | None = None,
    results: Sequence[Result] | None = None,
) -> None:
    """
    Write ``report.json`` and ``mismatches.csv`` (plus ``outputs.csv`` when results given).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": config,
        "wall_seconds": round(elapsed, 3),
        "rows_per_second": round(report.total / elapsed, 3) if elapsed else None,
        **report.summary(),
    }
    (out_dir / "report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with open(out_dir / "mismatches.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["index", "input", "expected", "actual", "type", "category"])
        for m in report.mismatches:
            writer.writerow([m.index, m.text, m.expected, m.actual, m.kind, m.category])
    if rows is not None and results is not None:
        by_index = {r.index: r for r in results}
        with open(out_dir / "outputs.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(["index", "input", "expected", "actual", "type", "seconds"])
            for row in rows:
                res = by_index.get(row.index)
                writer.writerow(
                    [
                        row.index,
                        row.text,
                        ALTERNATIVE_SEPARATOR.join(row.expected),
                        res.actual if res else "",
                        row.kind,
                        f"{res.seconds:.6f}" if res else "",
                    ]
                )


# ------------------------------------------------------------------------------ CLI


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("csv", type=Path, help="benchmark CSV with input,expected,type columns")
    parser.add_argument(
        "--workers", type=int, default=max(1, (multiprocessing.cpu_count() or 2) // 2)
    )
    parser.add_argument("--lang", default="ta")
    parser.add_argument("--direction", choices=("tn", "itn"), default="tn")
    parser.add_argument(
        "--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="FAR grammar cache"
    )
    parser.add_argument("--no-cache", action="store_true", help="compile grammars in every worker")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="only run the first N rows")
    parser.add_argument("--show", type=int, default=20, help="mismatches to print")
    parser.add_argument("--save-outputs", action="store_true", help="also write outputs.csv")
    parser.add_argument("--min-accuracy", type=float, default=0.0, help="exit 1 below this %%")
    parser.add_argument("--input-col", default="input")
    parser.add_argument("--expected-col", default="expected")
    parser.add_argument("--type-col", default="type")
    parser.add_argument("--quiet", action="store_true", help="no progress output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_rows(
        args.csv,
        limit=args.limit,
        input_col=args.input_col,
        expected_col=args.expected_col,
        type_col=args.type_col,
    )
    if not rows:
        print("no rows to evaluate", file=sys.stderr)
        return 1
    cache_dir: Path | None = None if args.no_cache else args.cache_dir

    if cache_dir is not None and args.workers > 1:
        t0 = time.perf_counter()
        build_normalizer(args.lang, args.direction, cache_dir)
        if not args.quiet:
            print(
                f"grammar ready in {time.perf_counter() - t0:.1f}s (cache: {cache_dir})",
                file=sys.stderr,
            )

    def progress(done: int, total: int) -> None:
        if not args.quiet:
            print(f"\r{done}/{total} rows", end="", file=sys.stderr, flush=True)

    start = time.perf_counter()
    results = run(
        rows,
        workers=args.workers,
        lang=args.lang,
        direction=args.direction,
        cache_dir=cache_dir,
        chunk_size=args.chunk_size,
        progress=progress,
    )
    elapsed = time.perf_counter() - start
    if not args.quiet:
        print(file=sys.stderr)

    report = evaluate(rows, results)
    print_report(report, show=args.show, elapsed=elapsed, workers=args.workers)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.report_dir / f"{args.csv.stem}_{stamp}"
    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    write_reports(
        report,
        out_dir,
        config=config,
        elapsed=elapsed,
        rows=rows if args.save_outputs else None,
        results=results if args.save_outputs else None,
    )
    print(f"reports written to {out_dir}")

    if report.errors:
        return 1
    return 0 if report.accuracy >= args.min_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())
