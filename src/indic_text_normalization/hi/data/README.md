# Hindi data tables

Tab-separated, NFC-normalized, two or three columns. `pynini.string_file` cannot carry a
notes column, so provenance is recorded here per table. Digits in keys are Devanagari
(U+0966 DEVANAGARI DIGIT ZERO – U+096F DEVANAGARI DIGIT NINE); ASCII input is mapped in
code. Nukta letters are stored NFC-decomposed (ड़ is U+0921 DEVANAGARI LETTER DDA + U+093C
DEVANAGARI SIGN NUKTA), as the engine normalizes all input to NFC.

| Table | Contents | Source / notes |
|---|---|---|
| `numbers/digit.tsv` | १-९ → एक … नौ | Written here from the standard (NCERT) forms: पाँच with U+0901 DEVANAGARI SIGN CANDRABINDU; ITN also accepts पांच |
| `numbers/zero.tsv` | ० → शून्य | Written here; ITN also accepts ज़ीरो/जीरो/सिफ़र |
| `numbers/teens_and_ties.tsv` | १०-९९ → the ninety lexical words (इक्कीस, बाईस, … निन्यानवे) | Written here from the standard forms with nukta (अड़तीस, सड़सठ); ITN accepts the common nukta-less and anusvara spellings |
| `numbers/scale_words.tsv` | scale word → trailing zeros → expand\|keep | Written here. `expand` multiplies the amount out (पाँच दशमलव पाँच हज़ार → 5500); `keep` leaves the written idiom (5.5 लाख, 1.5 अरब) |
| `numbers/quantity_words.tsv` | written scale word → spoken word → kind (`native`, `english`, `short`) | Written here. Native words (including the nukta-less हजार) and English `lakh/crore/million` follow the number after a space; the shorthands `L/cr/K/M/B` may be glued (₹15L). Read by the shared decimal and money taggers |
| `numbers/itn_prose_phrases.tsv` | phrases where a numeral word is an article, a pronoun or an approximation idiom | Written here; col 2 is the reason. Protected verbatim by the ITN prose tagger |
| `numbers/count_nouns.tsv` | nouns counted with a numeral (दिन, बार, रुपये …), col 2 a gloss | Written here. ITN converts a bare एक only before these words (plus the unit words), since एक is also the article |
| `numbers/itn_half_forms.tsv` | the idiomatic fractions → integer/fraction digits (डेढ़ → 1.5, ढाई → 2.5, साढ़े दस → 10.5, सवा दो → 2.25, पौने तीन → 2.75; the non-standard साढ़े एक/साढ़े दो ASR emits are accepted too); bare आधा/चौथाई/पौन are left as nouns | Generated here; 3 columns; ITN input only, also read as clock times (सवा दस बजे → 10:15) |
| `date/days.tsv` | ०१-३१ → day-of-month words | Generated from the number tables |
| `date/months.tsv` | ०१-१२ → जनवरी … दिसंबर | Written here (standard Hindi month names, फ़रवरी with nukta) |
| `date/year_suffix.tsv` | era abbreviations → spoken era | Written here: ई./ई.पू. (ईस्वी / ईसा पूर्व), सन्, AD/BC |
| `time/hours.tsv` | ०-२३ → hour words | Generated here from the number tables; 24 is not a valid hour |
| `time/minutes.tsv`, `time/seconds.tsv` | ०१-५९ → words | Generated here; no `60` row (10:60 is not a time) |
| `time/meridiem.tsv` | १-१२ → the day-part word for a written AM, then PM (सुबह, दोपहर, शाम, रात) | Written here. Hindi has no fixed AM/PM words, so the verbalizer picks the day part by the hour (10:30 AM → सुबह, 10:30 PM → रात, 6 PM → शाम) |
| `money/currency.tsv` | symbol/code → singular currency word | Written here, plus `रु./रु/रू.`, `₩ ₺ ৳ ₦` rows so every minor-currency pair is reachable |
| `money/currency_forms.tsv` | singular → plural, oblique (रुपया रुपये रुपये, पैसा पैसे पैसे; the loan currencies are invariant) | Written here; 3 columns |
| `money/major_minor_currencies.tsv` | major → minor unit (रुपया → पैसा, पाउंड → पेंस) | Written here |
| `money/currency_itn.tsv` | spoken currency word → symbol | Written here for ITN; includes the oblique रुपयों and the common spellings रुपए/रूपये/डालर/पौंड |
| `money/minor_unit_itn.tsv` | extra minor-unit word → symbol | Written here; only the rows `major_minor_currencies.tsv` crossed with `currency_forms.tsv` cannot supply (पैसों, पेनी, सेंट्स) |
| `measure/unit.tsv` | abbreviation → singular, plural unit (kg → किलोग्राम, किलोग्राम; hr → घंटा, घंटे) | Written here; 3 columns; no `st/nd/rd/th` rows so English ordinals survive; the prose words किलो/लीटर are count nouns, not units |
| `telephone/number.tsv` | ०-९ → digit words | Written here |
| `telephone/cues.tsv` | words after which a 4-6 digit run reads digit by digit (पिन कोड, OTP) | Written here; read by the shared telephone tagger |
| `whitelist/abbreviations.tsv` | abbreviation → expansion (डॉ. → डॉक्टर) | Written here |
| `whitelist/symbol.tsv` | symbol → spoken word | Translated here from the Telugu table; `-` absent (a lone hyphen is punctuation), `<` `>` absent (markup); `%` → प्रतिशत |
| `math_operations.tsv` | operator → word (used for `=` → बराबर) | Written here |

## Register and judgement calls (for the Hindi reviewer)

Formal written register was chosen for TN output. Items a native reviewer should confirm:

1. Spellings follow the NCERT standard: chandrabindu in `पाँच`, nukta in `हज़ार`, `करोड़`, `अड़तीस`,
   `साढ़े`, `फ़रवरी`. ITN accepts the anusvara and nukta-less spellings (`पांच`, `हजार`, `करोड`).
2. Every scale group is spaced and one is counted: `100 → एक सौ`, `1000 → एक हज़ार`,
   `1,00,000 → एक लाख`, `2024 → दो हज़ार चौबीस`, `1,50,000 → एक लाख पचास हज़ार`. ITN also accepts the
   bare `सौ` and `हज़ार` (`सौ बीस → 120`) while a bare `लाख`/`करोड़` stays a word.
3. Years 1100-1999 read as hundreds in dates (`15/08/1947 → … उन्नीस सौ सैंतालीस`, `1900 → उन्नीस
   सौ`); a plain `1947` reads `एक हज़ार नौ सौ सैंतालीस`, and ITN accepts both (`पंद्रह सौ → 1500`).
4. Negative sign `माइनस` (the loanword used in Hindi print); ITN also accepts the textbook `ऋण`.
   Decimal point `दशमलव` (ITN also accepts `पॉइंट`, `बिंदु`). Range `से` (`10-20 → दस से बीस`).
5. Fractions: `3/4 → तीन बटा चार`, `2 3/4 → दो पूर्णांक तीन बटा चार`; ITN also accepts `बटे`, `बाय`. Vulgar
   signs read as everyday words: `½ → आधा`, `¼ → चौथाई`, `¾ → पौन`, and with an integer take the
   idioms `1½ → डेढ़`, `2½ → ढाई`, `3½ → साढ़े तीन`, `2¼ → सवा दो`, `2¾ → पौने तीन`; ITN reads those back
   as decimals and, before `बजे`, as clock times (`सवा दस बजे → 10:15`, `पौने दस बजे → 9:45`).
6. Time: `10:30 → दस बजकर तीस मिनट`, `10:00 → दस बजे`, `10:00:30 → दस बजकर तीस सेकंड`; a written AM/PM
   becomes the day part for that hour (`10:30 AM → सुबह …`, `10:30 PM → रात …`, `2 PM → दोपहर …`,
   `6 PM → शाम …`). `X बजे` is always a clock time; `X घंटे` is a duration and is not converted.
7. Money: `₹1 → एक रुपया`, `₹50 → पचास रुपये`, `₹50.50 → पचास रुपये पचास पैसे`, `₹0.01 → एक पैसा`; the
   loan currencies are invariant (`$5 → पाँच डॉलर`). `₹5 करोड़ → पाँच करोड़ रुपये`.
8. Measure: most units are invariant (`5 kg → पाँच किलोग्राम`); `घंटा` and `महीना` take their plural
   after any count but one (`5 hr → पाँच घंटे`, `1 hr → एक घंटा`).
9. Hindi writes its postpositions as separate words, so no case suffix is ever glued to a digit;
   `2024में` (a typo) is split into `दो हज़ार चौबीस में`. Only the ordinal endings glue.
10. Ordinals carry gender and case: `5वाँ → पाँचवाँ`, `5वीं → पाँचवीं`, `5वें → पाँचवें` (`5वां`/`5वे` are
    accepted and written back with the chandrabindu); the first six are lexical and written with
    their own endings, `1ला → पहला`, `1ली → पहली`, `2रा → दूसरा`, `3री → तीसरी`, `4था → चौथा`, `6ठा → छठा`,
    and ITN writes them the same way (`पहली → 1ली`).
11. Percent reads postposed, `5% → पाँच प्रतिशत`.
12. A bare `एक` stays a word in ITN (it is also the article "a"); it converts before a count noun
    or unit (`एक दिन → 1 दिन`) and inside any longer number, date, time or amount.
13. `<` and `>` between digits stay as written: Hindi has no natural symbol-order reading.
