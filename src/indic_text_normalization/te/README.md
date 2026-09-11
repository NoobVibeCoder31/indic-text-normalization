# Telugu grammars — performance baseline

Reference numbers for the Telugu TN and ITN grammars, so a future change can be compared
against a known point rather than a remembered one. Same method and machine as
[the Tamil baseline](../ta/README.md).

Measured 2026-09-10, single-threaded, on an otherwise idle machine.

## Grammar compilation (cold, no cache)

| direction | build time | peak RSS | FAR size | classify states |
|---|---|---|---|---|
| TN | 93.3 s | 4,151 MB | 101 MB | 3,257,932 |
| ITN | 30.3 s | 415 MB | 8 MB | 213,827 |

## Loading from the FAR cache

| | |
|---|---|
| TN load | 0.55 s |
| ITN load | 0.10 s |
| resident after both loaded | 713 MB |

## Per-sentence latency

Median of 20 timed runs after one warm-up, both directions loaded in one process.

### TN (written → spoken)

| input | chars | median | min | max |
|---|---|---|---|---|
| `౧౨` | 2 | 1.2 ms | 1.1 | 2.5 |
| `ఈరోజు 15-06-2024 న ₹1,250.50 చెల్లించారు.` | 41 | 10.0 ms | 8.4 | 19.4 |
| `అతని ఫోన్ నంబర్ +91 9876543210 అవుతుంది.` | 40 | 9.0 ms | 7.7 | 14.6 |
| `ఉదయం 10:30 గంటలకు 5.5 కిలోగ్రాముల బియ్యం ₹2,499/- కి కొన్నాను.` | 62 | 8.7 ms | 6.7 | 16.3 |
| `2024లో 3/4 వంతు ప్రజలు 25% వృద్ధి చూశారు, అంటే ₹5 కోట్లు.` | 57 | 6.3 ms | 5.8 | 11.5 |
| **total across the five** | | **35 ms** | | |

### ITN (spoken → written)

| input | chars | median | min | max |
|---|---|---|---|---|
| `పన్నెండు` | 8 | 0.3 ms | 0.3 | 0.4 |
| `పదిహేను జూన్ … యాభై పైసలు` | 77 | 5.1 ms | 4.7 | 10.3 |
| `తొమ్మిది తొమ్మిది … ఏడు సున్నా` | 65 | 2.9 ms | 2.8 | 4.9 |
| `ఉదయం పది గంటల … ఐదు కిలోగ్రాముల బియ్యం` | 64 | 2.1 ms | 2.1 | 2.5 |
| `రెండు వేల ఇరవై నాలుగులో … ఇరవై ఐదు శాతం వృద్ధి` | 72 | 3.3 ms | 3.1 | 6.3 |
| **total across the five** | | **14 ms** | | |

## History

| date | change | ITN states | ITN build | ITN peak | ITN latency (5 samples) |
|---|---|---|---|---|---|
| 2026-09-10 | first measurement, before the shared-core refactor | 1,164,051 | 49 s | 1,522 MB | 1,099 ms |
| 2026-09-10 | reading graphs made input-deterministic (`sequential`), TN pre-pass moved to call time | 213,827 | 30 s | 415 MB | 14 ms |

Telugu TN also fell from 4,401,139 to 3,257,932 classify states (135 s / 7,695 MB to
93 s / 4,151 MB to build), because the tokenizer's spacing pre-pass is now composed with
the text at call time instead of being compiled into the sentence graph.
