# indic-text-normalization

> **This repository is developed AI-driven.** The grammars, tests and tooling are written
> with AI assistance and reviewed by humans before they land. Every behaviour change is
> gated the same way regardless of who or what wrote it: golden-file tests, idempotency
> sweeps, a round-trip census, and `black` / `ruff` / `mypy --strict`.
>
> **Contributions are very welcome** — see [Contributing](#contributing).

Accurate **text normalization (TN)** and **inverse text normalization (ITN)** for Indic
languages, with **low latency and small memory footprint** as first-class goals.

Today that is implemented as WFST grammars on
[pynini](https://www.openfst.org/twiki/bin/view/GRM/Pynini), using the tagger–verbalizer
architecture of
[NVIDIA NeMo-text-processing](https://github.com/NVIDIA/NeMo-text-processing). The
implementation is a means, not the point — see [Project direction](#project-direction).

Tamil is supported today. Telugu is in progress; Malayalam, Kannada and Hindi are planned.

## What it does

- **TN (written → spoken)** for TTS pipelines: `₹1,250.50` → `ஆயிரத்து இருநூற்று ஐம்பது ரூபாய் ஐம்பது பைசா`
- **ITN (spoken → written)** for ASR output: `இருபத்துமூன்று பேர் வந்தனர்` → `23 பேர் வந்தனர்`

Semiotic classes: cardinal, ordinal, decimal, fraction, date, time, money, measure,
telephone, range, plus whitelist/abbreviations, punctuation, and a pass-through word class.
Both Tamil (௦-௯) and ASCII digits are accepted in written form.

## Requirements

- **Linux x86_64** and **CPython 3.10–3.12**. This comes from `pynini`, which publishes
  wheels only for those; other platforms would need to build OpenFst from source.
- ~6 GB of free RAM to compile a grammar from scratch. This is a one-time cost — see
  [Caching](#caching).

## Install

There is no PyPI release yet, so install from the repository.

As a dependency:

```bash
uv add git+https://github.com/<org>/indic-text-normalization
# or, with pip
pip install git+https://github.com/<org>/indic-text-normalization
```

For development:

```bash
git clone https://github.com/<org>/indic-text-normalization
cd indic-text-normalization
uv sync                       # runtime + dev dependencies, from uv.lock
```

## Usage

```python
from indic_text_normalization import InverseNormalizer, Normalizer

tn = Normalizer(lang="ta")
tn.normalize("₹1,250.50")            # ஆயிரத்து இருநூற்று ஐம்பது ரூபாய் ஐம்பது பைசா
tn.normalize("10:30")                # பத்து மணி முப்பது நிமிடம்
tn.normalize("15-06-2024")           # பதினைந்து ஜூன் இரண்டாயிரத்து இருபத்துநான்கு
tn.normalize("3.14")                 # மூன்று புள்ளி ஒன்று நான்கு
tn.normalize("+91 9876543210")       # பிளஸ் ஒன்பது ஒன்று ஒன்பது எட்டு ...
tn.normalize("5வது வகுப்பு")          # ஐந்தாவது வகுப்பு

itn = InverseNormalizer(lang="ta")
itn.inverse_normalize("ஐம்பது ரூபாய்")                 # ₹50
itn.inverse_normalize("பத்து மணி முப்பது நிமிடம்")      # 10:30
itn.inverse_normalize("இருபத்துமூன்று பேர் வந்தனர்")     # 23 பேர் வந்தனர்
```

Whole sentences work too — each token is classified independently, and anything the
grammar does not recognise passes through untouched:

```python
tn.normalize("இன்று 15-06-2024 அன்று ₹1,250.50 செலுத்தப்பட்டது.")
# இன்று பதினைந்து ஜூன் இரண்டாயிரத்து இருபத்துநான்கு அன்று ஆயிரத்து இருநூற்று ஐம்பது ரூபாய் ஐம்பது பைசா செலுத்தப்பட்டது .
```

For a one-off call there are functional helpers, which build a grammar per call and so are
only appropriate for scripts:

```python
from indic_text_normalization import inverse_normalize, normalize

normalize("₹50", lang="ta")                    # ஐம்பது ரூபாய்
inverse_normalize("ஐம்பது ரூபாய்", lang="ta")   # ₹50
```

### Caching

Compiling a grammar takes a couple of minutes per direction. Pass `cache_dir` to compile
once and reload from an OpenFst FAR archive in under a second afterwards — do this for
anything long-running:

```python
tn = Normalizer(lang="ta", cache_dir="~/.cache/itn-grammars")
```

The API is functional and pure: transforms take `str` and return `str`, with no global
state and no I/O. Output is deterministic and does not depend on the system locale.

## Development

```bash
uv run pytest                 # golden-file, idempotency and round-trip tests
uv run black --check .
uv run ruff check
uv run mypy
```

Licensed under the Apache License 2.0 (`LICENSE`). The grammars build on
NeMo-text-processing (NVIDIA), Kenpath indic-text-normalization, and Google/Thrax by way
of NeMo — `NOTICE` records what came from where.

See `CLAUDE.md` for the full project rules.

## Benchmarks

`benchmarks/ta_tn_benchmark.csv` holds 10k+ Tamil TN rows (`input,expected,type`).
Run it in parallel and get accuracy per semiotic class plus a mismatch report:

```bash
uv run python benchmarks/run_benchmark.py benchmarks/ta_tn_benchmark.csv --workers 8
```

See `benchmarks/README.md` for the schema and how the dataset is generated, and
`benchmarks/perf_ta.py` for the latency and memory baseline.

## Adding a language

1. Create `src/indic_text_normalization/<lang>/` with `data/`, `tn/`, and `itn/`
   mirroring the `ta` package (shared logic lives in `core/`).
2. Register the grammar factories in `core/registry.py`.
3. Add golden data under `tests/data/<lang>/{tn,itn}/` and per-class tests.

## Project direction

The goal is TN and ITN for Indic languages that are **accurate, fast, and cheap in
memory**. Those three are the bar every approach is judged against.

**Why WFST today.** Finite-state grammars are deterministic and auditable — you can point
at the rule that produced an output — they need no training data, and they never
hallucinate. That makes them a good starting point for a domain where a wrong number is
worse than no output.

**What it costs.** Grammars are large and hand-built. Each language is months of
linguistic work, and the compiled machines are heavy: see
[`src/indic_text_normalization/ta/README.md`](src/indic_text_normalization/ta/README.md)
for measured build time, memory and per-sentence latency.

**What we are considering.** None of this is settled, and none of it is committed:

- A **small fine-tuned language model**, kept deliberately small and then **pruned and/or
  quantized**, if it can beat the grammars on latency and memory at comparable accuracy.
- A **hybrid**: grammars for the classes they already handle deterministically, a model for
  the messy tail — or a model that proposes and a grammar that verifies.
- **Any other approach.** If you have a better idea, open an issue. This is an open
  question, not a decided roadmap.

**How a replacement would be judged.** Measured with
[`benchmarks/perf_ta.py`](benchmarks/perf_ta.py) on the same pinned sentences, holding
accuracy on the golden tests and the round-trip census. "Faster" has to mean faster on the
same inputs, or it means nothing.

## Contributing

Contributions are welcome, and these are the areas where help goes furthest:

- **A new Indic language.** Start from [Adding a language](#adding-a-language); the Tamil
  package is the reference.
- **Coverage gaps**, especially ITN: colloquial and regional spoken forms, and shapes an
  ASR system actually emits.
- **Latency and memory.** Smaller grammars, cheaper composition, faster loading.
- **Alternative approaches** to the ones in [Project direction](#project-direction) — model
  based, hybrid, or something else. Open an issue to discuss before building.

Two rules worth knowing before you start, both from `CLAUDE.md`:

- **Every behaviour change ships with a test.** Add a golden case to
  `tests/data/<lang>/{tn,itn}/<class>.txt` in the same change, including cases that
  document an intentional rejection.
- **A change is not done until** `uv run black --check .`, `uv run ruff check`,
  `uv run mypy` and `uv run pytest` all pass.

When adding or changing a mapping, cite the source (Unicode chart, script grammar
reference) in the pull request, and flag any new runtime dependency or public API.
