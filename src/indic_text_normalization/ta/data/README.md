# Tamil data tables

Two-column, tab-separated, NFC-normalized. `pynini.string_file` cannot carry a notes
column, so provenance is recorded here per table.

| Table | Contents | Source / notes |
|---|---|---|
| `digits.tsv` | ASCII 0-9 ↔ Tamil digits U+0BE6–U+0BEF | Unicode Tamil block chart |
| `numbers/digit.tsv` | ௧-௯ → ஒன்று … ஒன்பது | Kenpath indic-text-normalization `ta` |
| `numbers/zero.tsv` | ௦ → பூஜ்யம் | Kenpath |
| `numbers/teens_and_ties.tsv` | ௧௦-௯௯ → joined compound words | Kenpath |
| `numbers/hundred.tsv` | ௧௦௦ → நூறு | Kenpath |
| `numbers/hundreds_exact.tsv` | ௨௦௦-௯௦௦ → இருநூறு … தொள்ளாயிரம் | Kenpath |
| `numbers/hundreds_combined.tsv` | ௨-௮ → இருநூற்று … எண்ணூற்று | Rewritten here: joined sandhi stems replace Kenpath's bare prefixes (முன்/நான்/…), which produced wrong forms like "நான் நூற்று" |
| `numbers/thousands.tsv` | thousands forms | Kenpath; no longer read by the grammar (scale words are listed in `tn/taggers/decimal.py`) |
| `numbers/itn_variants.tsv` | spaced spoken forms 0-99 → ASCII digits | Adapted from indic-num2words (`NUM_DICT["ta"]`); accepted as ITN input only |
| `numbers/itn_half_forms.tsv` | fused fractional words → integer/fraction digits (ஒன்றரை → 1.5) | Written here; 3 columns (word, integer part, fractional part), ITN input only |
| `ordinal/*.tsv` | ordinal suffixes and exceptions | Kenpath; the tagger now derives ஐந்தாவது-style stems morphologically |
| `date/{days,months,year_suffix}.tsv` | day/month numerals → words | Kenpath |
| `time/{hours,minutes,seconds}.tsv` | hours 0-24, minutes/seconds 1-59 → words | Kenpath; the `60` minute/second rows were removed (10:60 is not a time) |
| `money/currency.tsv` | symbol/code → currency word | Kenpath; ரூ./ரூ rows added here |
| `money/major_minor_currencies.tsv` | major → minor unit word | Kenpath |
| `money/currency_itn.tsv` | currency word → canonical symbol | Written here for ITN |
| `fraction/denominator_il.tsv` | locative -இல் form → cardinal word | Written here; regular locative morphology |
| `measure/unit.tsv` | unit abbreviation → spoken unit | Kenpath; `st` (stone) removed because it swallowed English ordinals (1st); `மீ`, `லி`, `சத` rows added |
| `telephone/*.tsv` | digit words and context cues | Kenpath |
| `whitelist/abbreviations.tsv` | abbreviation → expansion | Kenpath |
| `whitelist/symbol.tsv` | symbol → spoken word | Kenpath; `-` removed (a lone hyphen is punctuation, not minus — broke idempotency); `<` `>` removed (markup; spoken as விடக் குறைவு / விட அதிகம் only between digits by the tokenizer) |
| `math_operations.tsv` | operator → word (used for `=`) | Kenpath |

Open review items: "ஒன்று ஆயிரம்" vs the more idiomatic "ஓராயிரம்" for 1000; ஒன்று vs
ஓர்/ஒரு register variants are absorbed via multi-accept golden lines.
