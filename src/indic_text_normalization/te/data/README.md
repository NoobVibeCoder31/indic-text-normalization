# Telugu data tables

Tab-separated, NFC-normalized, two or three columns. `pynini.string_file` cannot carry a
notes column, so provenance is recorded here per table. Digits in keys are Telugu
(U+0C66 TELUGU DIGIT ZERO – U+0C6F TELUGU DIGIT NINE); ASCII input is mapped in code.

| Table | Contents | Source / notes |
|---|---|---|
| `numbers/digit.tsv` | ౧-౯ → ఒకటి … తొమ్మిది | Kenpath indic-text-normalization `te` |
| `numbers/zero.tsv` | ౦ → సున్నా | Kenpath |
| `numbers/teens_and_ties.tsv` | ౧౦-౯౯ → spaced compounds (ఇరవై ఒకటి) | Kenpath |
| `numbers/hundred.tsv` | ౧౦౦ → వంద | Written here (Kenpath had "ఒక వంద", never loaded) |
| `numbers/hundreds_exact.tsv` | ౨౦౦-౯౦౦ → రెండు వందలు … తొమ్మిది వందలు | Written here: plural exact hundreds |
| `numbers/hundreds_oblique.tsv` | ౨-౯ → రెండు వందల … | Written here: oblique stems before a remainder (205 → రెండు వందల ఐదు) |
| `numbers/scale_words.tsv` | scale word → trailing zeros → expand\|keep | Written here. `expand` multiplies the amount out (ఐదు దశాంశం ఐదు వేలు → 5500); `keep` leaves the written idiom (5.5 లక్షలు) |
| `numbers/quantity_words.tsv` | written scale word → spoken word → kind (`native`, `english`, `short`) | Written here. Native words and English `lakh/crore/million` follow the number after a space; the shorthands `L/cr/K/M/B` may be glued (₹15L). Read by the shared decimal and money taggers |
| `telephone/cues.tsv` | words after which a 4-6 digit run reads digit by digit (పిన్ కోడ్, OTP) | Written here; read by the shared telephone tagger |
| `numbers/itn_prose_phrases.tsv` | phrases where a numeral word is a pronoun or an approximation idiom | Written here; col 2 is the reason. Protected verbatim by the ITN prose tagger |
| `numbers/count_nouns.tsv` | nouns counted with a numeral (మంది, రోజు, ఓట్లు …), col 2 a gloss | Written here. TN reads `1 రోజు → ఒక రోజు` and `78,000 మంది → డెబ్బై ఎనిమిది వేల మంది` before these words (plus the unit words); ITN does not invert `ఒక` before them, since it is also the article |
| `numbers/itn_half_forms.tsv` | fused fractional words → integer/fraction digits (ఒకటిన్నర → 1.5, పదిన్నర → 10.5); bare అర/పావు are left as nouns | Written here; 3 columns; ITN input only |
| `date/days.tsv` | ౦౧-౩౧ → day-of-month words | Kenpath |
| `date/months.tsv` | ౦౧-౧౨ → జనవరి … డిసెంబర్ | Kenpath |
| `date/year_suffix.tsv` | era abbreviations → spoken era | Kenpath (`క్రి.శ.`) plus the standard `క్రీ.శ./క్రీ.పూ.`, `సా.శ.`, `AD/BC` rows added here |
| `time/hours.tsv` | ౦-౨౩ → hour words; ౧ → ఒంటి (clock one) | Generated here from the number tables; 24 is not a valid hour |
| `time/minutes.tsv`, `time/seconds.tsv` | ౦౧-౫౯ → words | Generated here; no `60` row (10:60 is not a time) |
| `money/currency.tsv` | symbol/code → singular currency word | Kenpath, plus `రూ./రూ`, `₩ ₺ ৳ ₦` rows so every minor-currency pair is reachable |
| `money/currency_forms.tsv` | singular → plural, oblique (రూపాయి రూపాయలు రూపాయల) | Written here; 3 columns |
| `money/major_minor_currencies.tsv` | major → minor unit (రూపాయి → పైసా) | Written here |
| `money/currency_itn.tsv` | spoken currency word (singular, plural, oblique) → symbol | Written here for ITN; superset of the TN symbols. Every major needs its oblique -ల row, which is the form that stands before a minor unit (ఐదు లీరాల యాభై కురుష్లు) |
| `money/minor_unit_itn.tsv` | extra minor-unit word → symbol | Written here; only the rows `major_minor_currencies.tsv` crossed with `currency_forms.tsv` cannot supply (the English plural పెన్స్) |
| `measure/unit.tsv` | abbreviation → singular, plural unit (kg → కిలోగ్రామ్, కిలోగ్రాములు) | Written here (Kenpath had 9 units); 3 columns; no `st/nd/rd/th` rows so English ordinals survive; the prose words కిలో/కేజీ are deliberately absent so `5 కిలోల బియ్యం` keeps its word |
| `telephone/number.tsv` | ౦-౯ → digit words | Kenpath |
| `whitelist/abbreviations.tsv` | abbreviation → expansion (డా. → డాక్టర్) | Written here (Kenpath rows were identity mappings) |
| `whitelist/symbol.tsv` | symbol → spoken word | Kenpath; `-` removed (a lone hyphen is punctuation), `<` `>` removed (markup; spoken only between digits by the tokenizer), duplicate Greek rows and the mojibake `ψ → సాই` rows dropped, `% → శాతం`, `υ → అప్సిలాన్` |
| `math_operations.tsv` | operator → word (used for `=`) | Kenpath, `%`/`.`/`-` glosses aligned with the formal register |

## Register and judgement calls (for the Telugu reviewer)

Formal / textbook register was chosen for TN output. Items a native reviewer should confirm:

1. Negative sign word `ఋణ` (U+0C0B TELUGU LETTER VOCALIC R): `-5 → ఋణ ఐదు`. ITN also accepts
   `మైనస్`, `రుణ`, `ఋణాత్మక`. The subtraction operator inside an equation reads `మైనస్`.
2. Decimal point `దశాంశం` (ITN also accepts `పాయింట్`, `పాయింటు`).
3. `19 → పందొమ్మిది` (Kenpath spelling); `పంతొమ్మిది` accepted by ITN.
4. Exact scale words are bare for a multiplier of one in cardinals (`1000 → వెయ్యి`, `1,00,000 → లక్ష`,
   `1,00,00,000 → కోటి`); in counting contexts a leading ఒకటి reads ఒక (`₹1 కోటి → ఒక కోటి రూపాయలు`,
   `1 లక్ష → ఒక లక్ష`).
5. `1100 → వెయ్యి వంద` (not `పదకొండు వందలు`); years 1100–1999 read as hundreds in dates
   (`1947 → పందొమ్మిది వందల నలభై ఏడు`), and ITN accepts both.
6. Fractions: `3/4 → నాలుగింట మూడు వంతులు`, `1/2 → రెండింట ఒక వంతు`; ITN also accepts `మూడు బై నాలుగు`.
    The vulgar signs read as everyday words: `½ → అర`, `¼ → పావు`, `¾ → ముప్పావు`, `1½ → ఒకటిన్నర`
    (a half fuses onto a vowel-final integer), `2¾ → రెండు మరియు ముప్పావు`; ITN reads those back as
    decimals (`5.5`, `2.75`). A written `3/4 వంతు` is not read with the noun twice.
7. Time: `1:00 → ఒంటి గంట`; `10:30 → పది గంటల ముప్పై నిమిషాలు`; `10:01 → పది గంటల ఒక నిమిషం`;
   AM/PM → `పూర్వాహ్నం` / `అపరాహ్నం`. Bare `X గంటలు` is a duration in ITN and is not converted.
8. Money: plural currency nouns (`₹50 → యాభై రూపాయలు`), oblique before paise
   (`₹50.50 → యాభై రూపాయల యాభై పైసలు`), `₹1 → ఒక రూపాయి`, `₹0.01 → ఒక పైసా`.
9. Measure: plural unit nouns after any count but one (`5 kg → ఐదు కిలోగ్రాములు`, `1 kg → ఒక కిలోగ్రామ్`).
10. Comparison signs between digits: `5<10 → ఐదు కంటే తక్కువ పది`, `10>5 → పది కంటే ఎక్కువ ఐదు`
    (word order follows the written symbol order).
11. Case suffixes attach verbatim to the last number word (`5కి → ఐదుకి`, `2024లో → …నాలుగులో`),
    with `-లు → -ల` before a suffix (`₹150కి → …రూపాయలకి`) and `-ం → -ాని-` before a dative
    (`10%కి → పది శాతానికి`).
12. Ordinals: `1వ → మొదటి`, `5వ → ఐదవ`, `20వ → ఇరవయ్యవ`, `5వో → ఐదో`; the scale words take
    a stem of their own (`1000వ → వెయ్యవ`, `1,00,000వ → లక్షవ`, `1,00,00,000వ → కోటవ`). `0వ` is
    left alone — Telugu has no ordinal of zero.
13. A minor unit belongs to one major currency, so `ఐదు డాలర్లు యాభై పైసలు` reads as two
    amounts (`$5 ₹0.50`), not `$5.50`. `సెంట్` alone is dollars and `పైసా` alone is rupees,
    because those majors come first in `money/currency_itn.tsv`.
14. ITN accepts a spoken sign word before a number, so `ప్లస్ ఐదు → +5` as `ఋణ ఐదు → -5`.
    An operator word between two numbers is therefore read as the sign of the second
    (`ఐదు ప్లస్ మూడు సమానం ఎనిమిది → 5 +3 సమానం 8`); `=` itself is a TN-only rewrite, which
    ITN leaves as it found it.
15. Counting: `1 <count noun> → ఒక <noun>` and a plural scale word takes its oblique before a count
    noun (`78,000 మంది → డెబ్బై ఎనిమిది వేల మంది`), for the nouns in `numbers/count_nouns.tsv` and the
    unit words. ITN reverses `ఒక` only before a unit word (`ఒక కిలోగ్రామ్ → 1 కిలోగ్రామ్`): before
    other nouns it is also the indefinite article (`ఒక రోజు`, "one day"), so `1 రోజు` does not round-trip.
16. Hundreds of crores are one place beyond the TN cardinal (which reads ten or more digits digit by
    digit), so ITN reads them itself: `ఐదు వందల కోట్లు → 5000000000`; money keeps the written idiom
    (`ఐదు వందల కోట్ల రూపాయలు → ₹500 కోట్లు`, `ఒక లక్ష కోట్ల రూపాయలు → ₹1 లక్ష కోట్లు`).
