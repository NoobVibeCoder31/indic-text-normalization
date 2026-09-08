# Changelog

All notable changes to this project. Versions follow semver; any change that alters the
output of an existing transform for any input is at least a minor bump.

## Unreleased (towards the first 0.1.0 release)

Tamil grammars only. Both directions change output for many inputs.

### ITN (spoken → written) — adversarial probe fixes

The findings are the ITN half of `temp/ta_probe_report.md`.

- **Cardinal sandhi.** The colloquial pre-map no longer destroys the sandhi forms TN
  itself emits: the raw input is now tried before the rewrite, and the spoken hundreds
  sandhi is split back. `இருபத்திரண்டு` → `22` (was unchanged),
  `நான்காயிரத்து நூற்றுப்பதினாறு` → `4116` (was `4000 116`), `நூற்றிரண்டு` → `102`.
  `முன்னூறு` (U+0BA9 spelling of 300) → `300`.
- **Case suffixes.** A suffix on a multi-word number is carried to the digits instead of
  stranding the tail: `இரண்டாயிரத்து இருபத்துநான்கில்` → `2024ல்` (was `2000 இருபத்துநான்கில்`),
  `ஐந்தில்` → `5ல்`.
- **Paise.** A single spoken minor-unit digit is tens of paise: `ஐந்து பைசா` → `₹0.05`
  (was `₹0.5`), `நூறு ரூபாய் ஐந்து பைசா` → `₹100.05`. Spoken `மைனஸ்` folds in for
  minor-unit-only amounts: `மைனஸ் ஐம்பது பைசா` → `-₹0.50`.
- **Scale words.** `ஆயிரம்` is expanded instead of kept as a written idiom, and the
  quantity idiom applies only to a short amount: `ஐந்து ஆயிரம் ரூபாய்` → `₹5000`
  (was `₹5 ஆயிரம்`, which was also non-idempotent), `ஐந்து கோடி ஐம்பது லட்சம் ரூபாய்` →
  `₹55000000` (was `₹50000050 லட்சம்`), `ஒன்றரை ஆயிரம்` → `1500`.
  A decimal keeps its scale word as a `quantity` field: `ஐந்து புள்ளி ஐந்து லட்சம்` →
  `5.5 லட்சம்` (was `5.500000`). A fused half amount now carries the currency:
  `ஒன்றரை லட்சம் ரூபாய்` → `₹1.5 லட்சம்`.
- **Currencies.** `money/currency_itn.tsv` has one row per output of the TN
  `money/currency.tsv` plus plurals, so `£50`, `¥100`, `₩1000`, `€50` round-trip.
  `பவுண்டு` is no longer a currency (it is the mass pound: `ஐந்து பவுண்டு` → `5 பவுண்டு`,
  was `£5`). New `money/minor_unit_itn.tsv` gives `ஐம்பது சென்ட்` → `$0.50`.
- **Time.** Hours are bound to 0-23 and minutes/seconds to 0-59, so an impossible clock
  falls back to plain numbers: `பத்து மணி அறுபது நிமிடம்` → `10 மணி 60 நிமிடம்` (was `10:60`),
  `இருபத்தைந்து மணிக்கு` → `25 மணிக்கு` (was `25:00`). Fused fractional hours read as clock
  times after `மணிக்கு`: `பத்தரை மணிக்கு` → `10:30`, `பத்தே கால் மணிக்கு` → `10:15` (was
  `பத்தே 0.25 மணிக்கு`); a bare `மணி` still keeps the duration reading (`பத்தரை மணி` →
  `10.5 மணி`), as for a bare hour. `பத்து முப்பது மணிக்கு` → `10:30` (was `10 30:00`), and a
  day-part word licenses the bare hour: `காலை பத்து மணி` → `காலை 10:00`.
- **Ordinals.** The `ம்` → `மா` and `நூறு` → `நூற்றா` stems invert, and an inflected tail
  after `வத-` is carried over: `ஆயிரமாவது` → `1000வது`, `பூஜ்யமாவது` → `0வது`,
  `ஐந்தாவதுக்கு` → `5வதுக்கு` (all were unchanged).
- **Fractions.** The regular locative is applied, so any denominator inverts:
  `ஏழில் இருபத்திரண்டு` → `22/7`, `ஆயிரத்தில் ஒன்று` → `1/1000`.
- **Telephone.** 10-to-12 digit spoken runs join, so the TN readings of `044-28230000`
  and `1800-425-1234` come back whole (were split `0442823000 0`). A written `+91` passes
  through as one token, making ITN's own telephone output idempotent.
- **Prose false positives.** `ஒரு` / `ஓர்` count as numbers only inside a money or clock
  reading, since they are also the indefinite article: `ஒரு நாள் ஒரு ராஜா` is unchanged
  (was `1 நாள் 1 ராஜா`) while `ஒரு ரூபாய்` → `₹1` and `ஒரு மணிக்கு` → `1:00` still work.
  `கால்` / `அரை` / `முக்கால்` read as words when another Tamil word follows
  (`கால் வலிக்கிறது` was `0.25 வலிக்கிறது`), and a small phrase table protects the pronoun
  `ஒன்று` (`ஒன்று சேர்`, `எல்லாம் ஒன்று`).
- **Tokenizer.** `[` and `]` are punctuation again and a value may hold a `"`, so
  `[ஐந்து]` → `[ 5 ]` and `"ஐந்து"` → `" 5 "` instead of being left unchanged. The added
  spaces match TN's own `[5]` → `[ ஐந்து ]`.
- `பூஜ்யம் X` is a digit run, not a zero-padded pair: `ஒன்று பூஜ்யம் ஒன்று` → `1 0 1`
  (was `1 01`).

New tests: `tests/ta/test_roundtrip.py` (a TN→ITN census of 640 integers covering every
sandhi shape) and an ITN golden-output idempotency case set in `tests/ta/test_idempotency.py`.
A wider manual sweep of 2 279 integers round-trips with 0 failures, against 167 of 1 800
(9.3 %) before this change.

Cost: the ITN grammar is now 4.3 M states, so a cold compile takes ≈210 s peaking at
≈5.8 GB (was ≈95 s) and the cached FAR is 114 MB.

### Code-review fixes

- **ITN no longer applies a TN-direction rewrite.** `itn/taggers/punctuation.py` was a copy
  of the TN tagger and mapped `=` → `சமம்`, so `inverse_normalize("5 = 5")` gave `5 சமம் 5`.
  ITN now leaves `=` alone. It still does not invert `சமம்` → `=`, so `5=5` does not
  round-trip; adding that would risk false positives on the ordinary word `சமம்`.
- **`Fst.project` no longer mutates shared state.** Both word taggers called
  `punctuation.graph.project("input")`, which is in-place and returns `self`, silently
  rewiring the graph the tokenizer also holds — and the next statement depended on that
  side effect, so reordering raised `FstOpError`. They now project a `.copy()`.
- **One date uses one separator.** The separator was chosen independently at each position,
  so `15-06/2024` and `2024/06-15` tagged as dates; they now fall through to the number and
  range readings.
- **Bare paise for every currency symbol.** `money.py` hard-coded six of the symbols in
  `currency.tsv`, so `₺.50`, `৳.50` and `₦.50` had no reading. The set is derived from the
  table now, so a new row needs no code change.
- **Dead money alias removed.** `cardinal_with_commas = cardinal_graph` was a leftover and
  the same graph was unioned with and without `-0.1`, so the discounted branch always won.
  Behaviour is unchanged; the effective weight is now explicit.
- Guarded the 3-column unpack of `itn_half_forms.tsv` (a trailing blank line, which 20 of
  the packaged TSVs already have and `test_data_integrity` permits, crashed the build).
- Tag parsing moved inside the verbalize `try`, so a parser error honours the documented
  "unprocessable input is returned unchanged" contract instead of escaping `normalize()`.
- `benchmarks/ta_tn_benchmark.csv` is generated, not committed (2 MB; CLAUDE.md wants
  discussion above 1 MB), so the three tests that need it now skip when it is absent
  instead of failing on a fresh clone.
- Capped the benchmark generator's top-up loop, which spun forever once the unique-span
  space was exhausted.
- `range(sys.maxunicode)` → `+ 1`, and the ~1.1 M-lookup punctuation scan is hoisted to
  module scope instead of running twice per direction on every build.
- Corrected two README examples that contradicted the goldens.

### TN (written → spoken) — leading `+` idempotency

A lone `+` was spoken as `கூட்டல்`, so any input where the `+` survived as its own token
changed on a second pass: `+000` → `+ பூஜ்யம் பூஜ்யம் பூஜ்யம்` → `கூட்டல் பூஜ்யம் பூஜ்யம் பூஜ்யம்`.
A brute-force sweep found 297 of 20 439 `+X` shapes affected (`+0-5`, `+0/5`, `+5வது`,
`+0,அ`, …). Found by `test_tn_random_idempotent`; it predates the ITN work above.

- A leading `+` is a sign read as `பிளஸ்` by the cardinal and decimal taggers, matching the
  telephone tagger's `+5` and the existing `-` handling: `+5` → `பிளஸ் ஐந்து`,
  `+000` → `பிளஸ் பூஜ்யம் பூஜ்யம் பூஜ்யம்`, `+5.5` → `பிளஸ் ஐந்து புள்ளி ஐந்து`.
- `+` is removed from `whitelist/symbol.tsv` and spoken by the tokenizer only between two
  digits, exactly as `-` was removed earlier and as `<`/`>` are handled. `5+3` →
  `ஐந்து கூட்டல் மூன்று` and `1+2=3` are unchanged.
- **Output change to note:** a lone `+` now stays `+` instead of reading `கூட்டல்`. This
  matches a lone `-`. All 151 `+` rows in `benchmarks/ta_tn_benchmark.csv` are telephone
  country codes and are unaffected.

After the fix, all 1-3 character combinations over the idempotency alphabet (9 723 strings)
are idempotent, with 0 failures.

### TN (written → spoken) — earlier adversarial probe fixes

See Section 5 of `temp/ta_probe_report.md` for the full table (engine field-order
blow-up, English scale words after a currency, `10:60`, case-suffix coverage, glued
operators, U+00A0 leak, Unicode pre-clean, URL passthrough).
