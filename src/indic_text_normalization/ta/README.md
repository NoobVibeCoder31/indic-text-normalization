# Tamil grammars — performance baseline

Reference numbers for the Tamil TN and ITN grammars, so a future change can be compared
against a known point rather than a remembered one.

Reproduce with [`benchmarks/perf.py`](../../../benchmarks/perf.py), which pins the
sample sentences below. **Compare against the same samples** — the script's sample lists
should not be edited casually, because changing one invalidates comparison with this table.

```bash
# Each direction builds in its own process: building both in one inflates the second
# under the first's memory pressure.
uv run python benchmarks/perf.py build tn  --lang ta --cache-dir /tmp/perf
uv run python benchmarks/perf.py build itn --lang ta --cache-dir /tmp/perf
uv run python benchmarks/perf.py measure   --lang ta --cache-dir /tmp/perf
```

## Reference machine

| | |
|---|---|
| CPU | AMD Ryzen AI 9 HX PRO 370 (12 cores / 24 threads, boost 5.16 GHz) |
| RAM | 30 GiB usable (32 GB installed) |
| Disk | SSD, ext4 on LVM |
| OS | Ubuntu 24.04.4 LTS, kernel 7.0.0-30-generic |
| Python | 3.12.3 |
| pynini | 2.1.6.post1 |

Measured 2026-09-10, single-threaded, on an otherwise idle machine.

## Grammar compilation (cold, no cache)

| direction | build time | peak RSS | FAR size | classify states |
|---|---|---|---|---|
| TN | 81.0 s | 3,840 MB | 86 MB | 2,886,548 |
| ITN | 41.1 s | 1,561 MB | 9 MB | 251,522 |

Compilation needs roughly **4 GB of free RAM** for TN; a machine with less will swap or be
killed. This cost is paid once — pass `cache_dir=` and the FAR is reused.

## Loading from the FAR cache

| | |
|---|---|
| TN load | 0.47 s |
| ITN load | 0.12 s |
| resident after both loaded | 631 MB |

Budget about **0.7 GB of RSS** to hold both directions in a long-running process.

## Per-sentence latency

Median of 20 timed runs after one warm-up, both directions loaded in one process.

### TN (written → spoken)

| input | chars | median | min | max |
|---|---|---|---|---|
| `௧௨` | 2 | 1.2 ms | 1.1 | 2.6 |
| `இன்று 15-06-2024 அன்று ₹1,250.50 செலுத்தப்பட்டது.` | 49 | 10.8 ms | 8.9 | 20.1 |
| `அவரின் தொலைபேசி எண் +91 9876543210 ஆகும்.` | 41 | 10.3 ms | 7.8 | 13.8 |
| `காலை 10:30 மணிக்கு 5.5 கிலோ அரிசி ₹2,499/- க்கு வாங்கினேன்.` | 59 | 7.8 ms | 7.1 | 12.8 |
| `2024ல் 3/4 பங்கு மக்கள் 25% வளர்ச்சி கண்டனர், அதாவது ₹5 கோடி.` | 61 | 5.9 ms | 5.1 | 7.4 |
| **total across the five** | | **36 ms** | | |

### ITN (spoken → written)

| input | chars | median | min | max |
|---|---|---|---|---|
| `பன்னிரண்டு` | 10 | 0.3 ms | 0.3 | 0.3 |
| `பதினைந்து ஜூன் … ஐம்பது பைசா` | 94 | 3.3 ms | 3.2 | 4.9 |
| `ஒன்பது ஒன்பது … ஏழு பூஜ்யம்` | 64 | 2.8 ms | 2.8 | 3.0 |
| `காலை பத்து மணி … ஐந்து கிலோ அரிசி` | 60 | 2.1 ms | 2.1 | 2.7 |
| `இரண்டாயிரத்து … இருபத்தைந்து சதவீதம் வளர்ச்சி` | 89 | 2.4 ms | 2.4 | 4.9 |
| **total across the five** | | **11 ms** | | |

## Reading these numbers

- **Latency depends on the input**, so these figures are a reference point, not a
  guarantee. Length matters less than what is in the sentence: cost follows how many
  semiotic classes the tokenizer must weigh, not how many characters there are.
- **Latency tracks classify-FST size almost exactly.** Profiling `normalize` shows
  `tottime ≈ cumtime` — the token parser, field permutation and verbalization together
  account for under 1% of a call. Any latency work is grammar-size work; Python-level
  optimization has nothing to bite on.
- The first call after loading is slower than the rest, hence the warm-up.

## History

| date | change | ITN states | ITN build | ITN peak | ITN latency (5 samples) |
|---|---|---|---|---|---|
| 2026-09-08 | after the ITN probe fixes | 4,334,292 | 210 s | 5,762 MB | — |
| 2026-09-08 | pre-map domain restricted, quarter stems bounded | 2,828,101 | 117 s | 4,029 MB | — |
| 2026-09-09 | date/time range-bound, decimal and time factored, TN money factored | 2,428,629 | 108 s | 3,335 MB | 900 ms |
| 2026-09-10 | reading graphs made input-deterministic (`sequential`), TN pre-pass moved to call time | 251,522 | 41 s | 1,561 MB | 11 ms |

The 2026-09-10 row is the `sequential()` change described in `dev-changelog.md`: an
inverted TN grammar emits its digits before reading any input, so every ITN tagger that
embedded one explored the whole digit skeleton at each word start. Determinizing on the
input side leaves the relation unchanged and cuts ITN to a twentieth of its size.
