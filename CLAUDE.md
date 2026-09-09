# CLAUDE.md — indic-text-normalization

Project rules for Claude Code and contributors. This is a **Python library for normalizing text in Indic scripts** (Devanagari, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Gurmukhi, Odia, and related scripts).

## Project layout & tooling

- Python **3.10+**. Source lives in `src/indic_text_normalization/`, tests in `tests/`.
- Manage environment and dependencies with **uv**: `uv sync` to set up, `uv add` to add dependencies, `uv run <cmd>` to execute tools. Commit `uv.lock`. Never use bare `pip`.
- Use `pyproject.toml` (PEP 621) for packaging — no `setup.py`.
- Format with **black** (line length 100, matching zspeech); lint with **ruff check** (never `ruff format`); type-check with **mypy --strict**. All public functions must have type hints.
- Dependencies: keep the core library dependency-light. Prefer the stdlib `unicodedata` first; add `PyICU` or `indic-nlp-library` only behind an optional extra (installed via `uv sync --extra icu`), never as a hard dependency.
- Run tests with `pytest`. A change is not done until `uv run black --check .`, `uv run ruff check`, `uv run mypy`, and `uv run pytest` all pass.

## Docstrings & comments

- Docstrings follow the **zspeech house style (NumPy format)**: section headings underlined with dashes, types wrapped in double backticks, descriptions indented 4 spaces, optional params suffixed `, optional (default=...)`. Class docstrings document constructor params under `Attributes`; use `Raises` for exceptions and `Example` with doctest `>>>` lines where a usage example helps. Template:

  ```python
  def to_language(language_code: str) -> Language:
      """
      Resolve a language code to its Language enum.

      Parameters
      ----------
      language_code : ``str``
          The language code for which the Language enum is required.

      Returns
      -------
      ``Language``
          The Language enum for the given language code.

      Raises
      ------
      ``ValueError``
          If the language code is not supported.
      """
  ```

- **Default docstring is a short summary of at most 3 lines.** Add full `Parameters`/`Returns`/`Raises` sections only when necessary — public API whose behavior or edge cases are not obvious from the signature.
- **Comments are rare.** Add one only where genuinely important — a non-obvious constraint, pitfall, or hackish fix — and **never longer than 1 line**. Never narrate what the code does; the code and docstrings carry that.
- Any lint/type suppression (`# noqa`, `# type: ignore`) must carry the specific rule code.
- The code-point rule below applies inside docstrings and comments too: refer to characters by code point + name.

## Unicode correctness rules (non-negotiable)

1. **Default to NFC.** All normalization pipelines produce NFC output unless the caller explicitly requests otherwise.
2. **Never apply blanket NFKC/NFKD to Indic text.** Compatibility normalization destroys meaningful distinctions. Apply compatibility mappings only via explicit, script-aware rules.
3. **Preserve ZWJ (U+200D) and ZWNJ (U+200C) by default.** They are semantically meaningful (e.g. Malayalam chillu fallbacks, Devanagari conjunct control). Stripping them must be an opt-in flag, never the default.
4. **Handle nukta forms explicitly.** Precomposed nukta characters (e.g. क़ U+0958) vs. base + nukta (क + U+093C) must be unified per script through explicit mapping tables, with the chosen canonical form documented per script.
5. **Never index or slice by code point for user-visible operations.** Operate on grapheme clusters where boundaries matter (use `regex` module `\X` or ICU break iterators).
6. Work with `str` internally everywhere. Encode/decode (UTF-8 only) at I/O boundaries. Never use `bytes` for text logic.
7. Refer to characters in code and comments by **code point + name** (e.g. `U+0BBE TAMIL VOWEL SIGN AA`), not by the raw glyph alone — glyphs are ambiguous in review and in editors.
8. Digit normalization (Devanagari ०-९, Tamil ௦-௯, etc. ↔ ASCII) must be a separate, opt-in transform — never bundled silently into general normalization.

## Script-specific rules

- Every script gets its own module (`scripts/devanagari.py`, `scripts/tamil.py`, …) implementing a common interface; shared logic lives in a base module. No giant if/elif script dispatch inside transforms.
- Script detection must be range-based on Unicode blocks and must handle **mixed-script strings** (normalize each run per its own script; leave Latin/ASCII runs untouched unless asked).
- Mapping tables live in **data files** (JSON/TSV under `src/.../data/`), not hard-coded dicts scattered through logic. Each table entry needs a comment or `notes` field citing why the mapping exists (Unicode chart, ISCII legacy, common typo, etc.).
- Legacy-encoding conversion (ISCII, TSCII, non-Unicode fonts) is out of scope unless explicitly added as a separate subpackage.

## Testing rules

- Every normalization rule requires **golden-file tests**: input → expected output pairs stored in UTF-8 test data files under `tests/data/<script>/`, one case per line with a description.
- Test data files must be reviewed with `hexdump`/code-point dumps in mind — invisible characters (ZWJ/ZWNJ, combining marks) are the whole point of this project. Never let an editor or formatter "clean up" test data files; exclude `tests/data/` from black and any pre-commit whitespace hooks.
- **Every fix ships with a unit test case, no exceptions.** Any change that alters grammar behavior (a bug fix, a weight change, a data-table edit) adds a golden regression case to `tests/data/<lang>/{tn,itn}/<class>.txt` in the same change — including cases that document intentional rejections (e.g. an invalid date falling back to a number reading). A fix without a test case is not done.
- **After changing a semiotic class, run that class's unit tests before anything else**: `uv run pytest tests/<lang>/test_<class>.py` (e.g. `uv run pytest tests/ta/test_date.py` after touching `ta/*/taggers/date.py`, its verbalizers, or its data files). A change to `cardinal` also requires the classes that consume it (decimal, fraction, ordinal, date, time, money) plus `test_idempotency.py`. Run the full suite before finishing the task.
- Test **idempotency** for every transform: `normalize(normalize(x)) == normalize(x)` must hold, property-tested with `hypothesis` over the relevant Unicode ranges.
- Test round-trip safety where a transform claims reversibility.
- Include at least one mixed-script and one empty/whitespace-only case per transform.

## API design rules

- Public API is functional and pure: transforms take `str`, return `str`, no global state, no I/O.
- Configuration via explicit keyword-only arguments or a frozen config dataclass — not module-level flags or environment variables.
- Deterministic and locale-independent: output must never depend on system locale, `LANG`, or platform.
- Follow semver. Any change that alters the output of an existing transform for any input is at least a **minor** version bump and must be called out in the changelog with examples.

## Workflow rules

- Branch from `master`; never commit directly to `master`. Commit messages: imperative mood, ≤ 72-char subject.
- Never commit: virtualenvs, `__pycache__`, `.pytest_cache`, large corpora (> 1 MB test data needs discussion first), scraped text of unclear license (repo is MIT — all included data must be MIT-compatible).
- When adding or changing a mapping, cite the authoritative source (Unicode chart, script grammar reference) in the PR description.
- Do not add new runtime dependencies, new scripts, or new public API without flagging it explicitly in the PR/summary.
