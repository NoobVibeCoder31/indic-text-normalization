# Tamil grammars — performance baseline

Reference numbers for the Tamil TN and ITN grammars, so a future change can be compared
against a known point rather than a remembered one.

Reproduce with [`benchmarks/perf_ta.py`](../../../benchmarks/perf_ta.py), which pins the
sample sentences below. **Compare against the same samples** — the script's sample lists
should not be edited casually, because changing one invalidates comparison with this table.

```bash
# Each direction builds in its own process: building both in one inflates the second
# under the first's memory pressure.
uv run python benchmarks/perf_ta.py build tn  --cache-dir /tmp/perf
uv run python benchmarks/perf_ta.py build itn --cache-dir /tmp/perf
uv run python benchmarks/perf_ta.py measure   --cache-dir /tmp/perf
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

Measured 2026-09-09, single-threaded, on an otherwise idle machine.

## Grammar compilation (cold, no cache)

| direction | build time | peak RSS | FAR size | classify states |
|---|---|---|---|---|
| TN | 115.1 s | 5,466 MB | 104 MB | 3,506,577 |
| ITN | 108.4 s | 3,335 MB | 71 MB | 2,428,629 |

Compilation needs roughly **6 GB of free RAM** for TN; a machine with less will swap or be
killed. This cost is paid once — pass `cache_dir=` and the FAR is reused.

## Loading from the FAR cache

| | |
|---|---|
| TN load | 0.92 s |
| ITN load | 0.49 s |
| resident after both loaded | 1,134 MB |

Budget about **1.2 GB of RSS** to hold both directions in a long-running process.

## Per-sentence latency

Median of 20 timed runs after one warm-up, both directions loaded in one process.

### TN (written → spoken)

| input | chars | median | min | max |
|---|---|---|---|---|
| `௧௨` | 2 | 1.3 ms | 1.2 | 2.8 |
| `இன்று 15-06-2024 அன்று ₹1,250.50 செலுத்தப்பட்டது.` | 49 | 13.7 ms | 9.2 | 17.6 |
| `அவரின் தொலைபேசி எண் +91 9876543210 ஆகும்.` | 41 | 9.5 ms | 7.4 | 10.5 |
| `காலை 10:30 மணிக்கு 5.5 கிலோ அரிசி ₹2,499/- க்கு வாங்கினேன்.` | 59 | 6.5 ms | 6.2 | 8.3 |
| `2024ல் 3/4 பங்கு மக்கள் 25% வளர்ச்சி கண்டனர், அதாவது ₹5 கோடி.` | 61 | 5.8 ms | 5.6 | 7.9 |
| **total across the five** | | **37 ms** | | |

### ITN (spoken → written)

| input | chars | median | min | max |
|---|---|---|---|---|
| `பன்னிரண்டு` | 10 | 10.0 ms | 9.6 | 10.6 |
| `பதினைந்து ஜூன் … ஐம்பது பைசா` | 94 | 285.6 ms | 266.9 | 317.6 |
| `ஒன்பது ஒன்பது … ஏழு பூஜ்யம்` | 64 | 196.6 ms | 178.0 | 220.7 |
| `காலை பத்து மணி … ஐந்து கிலோ அரிசி` | 60 | 202.6 ms | 175.7 | 218.9 |
| `இரண்டாயிரத்து … இருபத்தைந்து சதவீதம் வளர்ச்சி` | 89 | 204.9 ms | 190.2 | 222.1 |
| **total across the five** | | **900 ms** | | |

## Reading these numbers

- **Latency depends on the input**, so these figures are a reference point, not a
  guarantee. Length matters less than what is in the sentence: the 61-character TN sample
  is faster than the 49-character one, because cost follows how many semiotic classes the
  tokenizer must weigh, not how many characters there are.
- **ITN is roughly 20× slower per sentence than TN.** Its grammar is smaller (2.4 M vs
  3.5 M states) but its inputs are many short word tokens, each of which the tokenizer
  must arbitrate between the number classes, where TN's digits commit early.
- **Latency tracks classify-FST size almost exactly.** Profiling `normalize` shows
  `tottime ≈ cumtime` — the token parser, field permutation and verbalization together
  account for under 1% of a call. Any latency work is grammar-size work; Python-level
  optimization has nothing to bite on.
- The first call after loading is slower than the rest, hence the warm-up.

## History

| date | change | ITN states | ITN build | ITN peak | TN→ITN round trip |
|---|---|---|---|---|---|
| 2026-09-08 | after the ITN probe fixes | 4,334,292 | 210 s | 5,762 MB | ~544 ms |
| 2026-09-08 | pre-map domain restricted, quarter stems bounded | 2,828,101 | 117 s | 4,029 MB | 383 ms |
| 2026-09-09 | date/time range-bound, decimal and time factored, TN money factored | 2,428,629 | 108 s | 3,335 MB | 264 ms |

The round-trip column is `inverse_normalize(normalize(n))` over the integers 300-399,
which is a different workload from the sentence samples above and is not comparable to
them; it is kept because the three rows were measured the same way.
