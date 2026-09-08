# Tamil data tables

Two-column, tab-separated, NFC-normalized. `pynini.string_file` cannot carry a notes
column, so provenance is recorded here per table.

| Table | Contents | Source / notes |
|---|---|---|
| `digits.tsv` | ASCII 0-9 ↔ Tamil digits U+0BE6–U+0BEF | Unicode Tamil block chart; **not read by any grammar** — `core/scripts.py` builds the same pair from the block start |
| `numbers/digit.tsv` | ௧-௯ → ஒன்று … ஒன்பது | Kenpath indic-text-normalization `ta` |
| `numbers/zero.tsv` | ௦ → பூஜ்யம் | Kenpath |
| `numbers/teens_and_ties.tsv` | ௧௦-௯௯ → joined compound words | Kenpath |
| `numbers/hundred.tsv` | ௧௦௦ → நூறு | Kenpath |
| `numbers/hundreds_exact.tsv` | ௨௦௦-௯௦௦ → இருநூறு … தொள்ளாயிரம் | Kenpath |
| `numbers/hundreds_combined.tsv` | ௨-௮ → இருநூற்று … எண்ணூற்று | Rewritten here: joined sandhi stems replace Kenpath's bare prefixes (முன்/நான்/…), which produced wrong forms like "நான் நூற்று" |
| `numbers/thousands.tsv` | thousands forms | Kenpath; no longer read by the grammar (scale words are listed in `tn/taggers/decimal.py`) |
| `numbers/itn_variants.tsv` | spaced spoken forms 0-99 → ASCII digits | Adapted from indic-num2words (`NUM_DICT["ta"]`); accepted as ITN input only |
| `numbers/itn_articles.tsv` | ஒரு / ஓர் → 1 | Split out of `itn_variants.tsv`: these are also the indefinite article, so they count as numbers only inside a money/time reading |
| `numbers/itn_half_forms.tsv` | fused fractional words → integer/fraction digits (ஒன்றரை → 1.5) | Written here; 3 columns (word, integer part, fractional part), ITN input only |
| `numbers/itn_ambiguous_words.tsv` | number words that are also ordinary words | Written here; col 2 is the reason. ITN keeps these as words when another Tamil word follows (கால் வலிக்கிறது) |
| `numbers/itn_prose_phrases.tsv` | phrases where a numeral is a pronoun/idiom | Written here; col 2 is the reason. Protected verbatim by the ITN prose tagger |
| `ordinal/*.tsv` | ordinal suffixes and exceptions | Kenpath; **not read by any grammar** — both taggers derive ஐந்தாவது-style stems morphologically. Kept for provenance only |
| `date/{days,months,year_suffix}.tsv` | day/month numerals → words | Kenpath |
| `time/{hours,minutes,seconds}.tsv` | hours 0-24, minutes/seconds 1-59 → words | Kenpath; the `60` minute/second rows were removed (10:60 is not a time) |
| `money/currency.tsv` | symbol/code → currency word | Kenpath; ரூ./ரூ rows added here |
| `money/major_minor_currencies.tsv` | major → minor unit word | Kenpath; **not read by any grammar** — the TN money verbalizer carries the mapping inline. Kept for provenance only |
| `money/currency_itn.tsv` | currency word → canonical symbol | Written here for ITN; one row per output of `money/currency.tsv` plus plurals. பவுண்டு is absent on purpose — that is the mass pound in `measure/unit.tsv`, the currency word is பவுண்ட் |
| `money/minor_unit_itn.tsv` | minor unit word → major currency symbol | Written here for ITN; ஐம்பது பைசா → ₹0.50, ஐம்பது சென்ட் → $0.50 |
| `fraction/denominator_il.tsv` | locative -இல் form → cardinal word | Written here; the 28 explicit forms of the TN fraction verbalizer. The ITN tagger also applies the regular locative, so any denominator round-trips |
| `measure/unit.tsv` | unit abbreviation → spoken unit | Kenpath; `st` (stone) removed because it swallowed English ordinals (1st); `மீ`, `லி`, `சத` rows added |
| `telephone/*.tsv` | digit words and context cues | Kenpath; only `number.tsv` is read. `mobile_context.tsv` / `landline_context.tsv` are **not read by any grammar** (they would drive OTP/PIN readings, which are unimplemented) |
| `whitelist/abbreviations.tsv` | abbreviation → expansion | Kenpath |
| `whitelist/symbol.tsv` | symbol → spoken word | Kenpath; `-` removed (a lone hyphen is punctuation, not minus — broke idempotency); `<` `>` removed (markup; spoken as விடக் குறைவு / விட அதிகம் only between digits by the tokenizer) |
| `math_operations.tsv` | operator → word (used for `=`) | Kenpath |

Open review items: "ஒன்று ஆயிரம்" vs the more idiomatic "ஓராயிரம்" for 1000; ஒன்று vs
ஓர்/ஒரு register variants are absorbed via multi-accept golden lines.
