# Changelog

## Unreleased - [0.3.0]

### 🎨 Added

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
