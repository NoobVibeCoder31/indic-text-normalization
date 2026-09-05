# Benchmarks

Accuracy and throughput benchmarks for the WFST normalizers. Tamil TN (written -> spoken)
is covered today.

## Files

| File | Purpose |
|---|---|
| `ta_tn_benchmark.csv` | 10k+ rows `input,expected,type` for Tamil TN |
| `run_benchmark.py` | Parallel runner: correct/mismatched counts, per-type accuracy, reports |
| `generate_ta_tn.py` | Seeded generator that produced the CSV (`--verify` diffs against the grammar) |
| `ta_reference.py` | Pure-Python reference verbalizer used for the `expected` column |

## Running

```bash
uv run python benchmarks/run_benchmark.py benchmarks/ta_tn_benchmark.csv --workers 8
```

Useful flags: `--limit N` (first N rows), `--workers 1` (in-process, easier to profile),
`--direction itn`, `--show 50` (mismatches to print), `--save-outputs` (every row's output),
`--min-accuracy 99.5` (exit 1 below the threshold), `--input-col/--expected-col/--type-col`
(other header names). Grammars compile once into `benchmarks/.far_cache/` and every worker
loads the FAR archive; `--no-cache` compiles in each worker instead.

Each run writes `benchmarks/reports/<csv-stem>_<UTC timestamp>/`:

- `report.json` – totals, accuracy, per-type table, mismatch categories, latency
  percentiles, slowest rows, run configuration;
- `mismatches.csv` – `index,input,expected,actual,type,category`;
- `outputs.csv` – with `--save-outputs`.

Mismatch categories: `unchanged` (the grammar left the input as is), `whitespace_only`,
`other`, `error` (an exception was raised).

## CSV schema

- Header `input,expected,type`; UTF-8, NFC, no leading/trailing whitespace, unique inputs.
- `expected` may hold several accepted outputs separated by `~`, the same convention as
  `tests/data/`. This is used where two spoken forms are both accepted, e.g. `150` ->
  `நூற்று ஐம்பது~நூற்றைம்பது`.
- `type` is the semiotic class: `cardinal, decimal, fraction, date, time, money, measure,
  ordinal, telephone, range, whitelist`, plus `mixed` (two spans of different classes in
  one sentence) and `word` (plain sentences, negative controls).

About 40% of rows are bare spans (`15-06-2024`), 60% embed the span in a short Tamil
carrier sentence (`கூட்டம் 15-06-2024 அன்று நடந்தது.`); roughly 10% of numeric spans use
Tamil digits U+0BE6–U+0BEF.

## How the dataset was built

`generate_ta_tn.py` draws spans per class with a fixed seed (`--seed 20260905`) and
computes `expected` with `ta_reference.py`, which reuses only the lexical tables under
`src/indic_text_normalization/ta/data/` and re-implements the composition rules (sandhi,
`ஆயிரம்` fusing, `ஒரு` before scale words, locative suffixes, minor-currency scaling, ...).

```bash
uv run python benchmarks/generate_ta_tn.py --verify   # regenerate and diff against the grammar
```

### Regression rows for shapes the benchmark exposed

The first benchmark run surfaced five grammar bugs, since fixed; 30 fixed rows (5 per
shape) stay in the dataset as regressions:

| Shape | Example | Now |
|---|---|---|
| 3-digit groupings | `1,000,000` | `பத்து இலட்சம்` (Indian idiom, no மில்லியன்) |
| Single-digit day/month dates | `5/4/2024` | `ஐந்து ஏப்ரல் இரண்டாயிரத்து இருபத்துநான்கு` |
| Zero seconds / zero minutes | `9:30:00`, `9:00:07` | `ஒன்பது மணி முப்பது நிமிடம்`, `ஒன்பது மணி ஏழு வினாடி` |
| Negative money | `-₹50` | `மைனஸ் ஐம்பது ரூபாய்` |
| Hyphenated ordinal `N-வது` | `12-வது` | `பன்னிரண்டாவது` |

Also observed: exact tens 150/160/170/180 fuse (`நூற்றைம்பது`) for Tamil-digit input but
stay spaced (`நூற்று ஐம்பது`) for ASCII input; both forms are accepted via `~`.

The FAR cache under `benchmarks/.far_cache/` is keyed by a hash of the grammar sources,
so editing the grammar automatically triggers a recompile on the next run.
