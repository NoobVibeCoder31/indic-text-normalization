# Changelog

## Unreleased - [0.2.0]

### 🎨 Added

- [TN] [ITN] [ml] Add Malayalam text normalization and inverse text normalization grammars:
  `23 → ഇരുപത്തിമൂന്ന്`, `2024 → രണ്ടായിരത്തി ഇരുപത്തിനാല്`, `₹150ന് → നൂറ്റിയൻപത് രൂപയ്ക്ക്`,
  `10:30 AM → രാവിലെ പത്ത് മണി മുപ്പത് മിനിറ്റ്`, `5-ാം → അഞ്ചാം`; ITN `അഞ്ചാം ക്ലാസ് → 5-ാം ക്ലാസ്`,
  `അൻപത് രൂപയ്ക്ക് → ₹50ന്`.
- [core] Shared TN and ITN taggers in `core/tn_taggers` and `core/itn_taggers`, bound to a
  language through `core/profile.LanguageProfile` and a `CardinalBase` subclass; shared
  verbalizers for languages whose nouns do not inflect (`InvariantMeasureFst`,
  `InvariantMoneyFst`, `InvariantTimeFst`, `QuantityDecimalFst`) and a day-part-by-hour
  reading of AM/PM (`time/meridiem.tsv`). Telugu is rebuilt on the shared taggers with
  identical output; its quantity words and telephone cue words move to
  `numbers/quantity_words.tsv` and `telephone/cues.tsv`.

### 🐛 Fixed

- [ITN] [te] A written glued suffix after a hyphen (`2024-లో`) now passes through ITN whole
  instead of being split at the hyphen.

## Unreleased - [0.1.0]

### 🎨 Added

- [TN] [ITN] [ta] Add Tamil text normalization and inverse text normalization grammars
- [TN] [ITN] [te] Add Telugu text normalization and inverse text normalization grammars
