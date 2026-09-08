# indic-text-normalization

WFST-based text normalization (TN) and inverse text normalization (ITN) for Indic
languages, built on [pynini](https://www.openfst.org/twiki/bin/view/GRM/Pynini) with the
tagger–verbalizer architecture of
[NVIDIA NeMo-text-processing](https://github.com/NVIDIA/NeMo-text-processing).

Tamil is supported today; Malayalam, Telugu, Kannada, and Hindi are planned.

## What it does

- **TN (written → spoken)** for TTS pipelines: `₹1,250.50` → `ஆயிரத்து இருநூற்று ஐம்பது ரூபாய் ஐம்பது பைசா`
- **ITN (spoken → written)** for ASR output: `இருபத்துமூன்று பேர் வந்தனர்` → `23 பேர் வந்தனர்`

Semiotic classes: cardinal, ordinal, decimal, fraction, date, time, money, telephone,
plus whitelist/abbreviations, punctuation, and a pass-through word class. Both Tamil
(௦-௯) and ASCII digits are accepted in written form.

## Install

Requires Linux x86_64 and Python 3.10–3.12 (pynini ships wheels only for those).

```bash
uv sync
```

## Usage

```python
from indic_text_normalization import Normalizer, InverseNormalizer

tn = Normalizer(lang="ta")
tn.normalize("10:30")            # பத்து மணி முப்பது நிமிடம்
tn.normalize("15-06-2024")       # பதினைந்து ஜூன் இரண்டாயிரத்து இருபத்துநான்கு

itn = InverseNormalizer(lang="ta")
itn.inverse_normalize("பத்து மணி முப்பது நிமிடம்")   # 10:30
itn.inverse_normalize("ஐம்பது ரூபாய்")                # ₹50
```

Grammar compilation takes a couple of minutes per direction; pass `cache_dir` to compile
once and reload from an OpenFst FAR archive:

```python
tn = Normalizer(lang="ta", cache_dir="~/.cache/itn-grammars")
```

## Development

```bash
uv run pytest                 # golden-file, idempotency and round-trip tests
uv run black --check .
uv run ruff check
uv run mypy
```

See `CLAUDE.md` for the full project rules and `NOTICE` for third-party attributions
(NeMo-text-processing, Kenpath indic-text-normalization; spoken-number variants adapted
from [indic-num2words](https://github.com/raj-sutariya/indic-num2words)).

## Benchmarks

`benchmarks/ta_tn_benchmark.csv` holds 10k+ Tamil TN rows (`input,expected,type`).
Run it in parallel and get accuracy per semiotic class plus a mismatch report:

```bash
uv run python benchmarks/run_benchmark.py benchmarks/ta_tn_benchmark.csv --workers 8
```

See `benchmarks/README.md` for the schema and how the dataset is generated.

## Adding a language

1. Create `src/indic_text_normalization/<lang>/` with `data/`, `tn/`, and `itn/`
   mirroring the `ta` package (shared logic lives in `core/`).
2. Register the grammar factories in `core/registry.py`.
3. Add golden data under `tests/data/<lang>/{tn,itn}/` and per-class tests.
