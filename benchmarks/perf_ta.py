"""
Reproducible performance baseline for the Tamil grammars.

Prints cold-build, cache-load and per-sample timings over a pinned sample set, so runs
taken months apart are comparable. Numbers from a reference machine are recorded in
``src/indic_text_normalization/ta/README.md``.

Build each direction in its own process, because building both in one inflates the
second under the first's memory pressure::

    uv run python benchmarks/perf_ta.py build tn  --cache-dir /tmp/perf
    uv run python benchmarks/perf_ta.py build itn --cache-dir /tmp/perf
    uv run python benchmarks/perf_ta.py measure   --cache-dir /tmp/perf
"""

import argparse
import logging
import resource
import statistics
import time
from collections.abc import Callable

from indic_text_normalization import InverseNormalizer, Normalizer
from indic_text_normalization.core.cache import far_path

# Pinned so a future run compares the same sentences. Do not edit casually: changing a
# sample invalidates comparison with the recorded baseline.
TN_SAMPLES = [
    "௧௨",
    "இன்று 15-06-2024 அன்று ₹1,250.50 செலுத்தப்பட்டது.",
    "அவரின் தொலைபேசி எண் +91 9876543210 ஆகும்.",
    "காலை 10:30 மணிக்கு 5.5 கிலோ அரிசி ₹2,499/- க்கு வாங்கினேன்.",
    "2024ல் 3/4 பங்கு மக்கள் 25% வளர்ச்சி கண்டனர், அதாவது ₹5 கோடி.",
]
ITN_SAMPLES = [
    "பன்னிரண்டு",
    "பதினைந்து ஜூன் இரண்டாயிரத்து இருபத்துநான்கு அன்று ஆயிரத்து இருநூற்று ஐம்பது ரூபாய் ஐம்பது பைசா",
    "ஒன்பது ஒன்பது நான்கு மூன்று இரண்டு பூஜ்யம் ஆறு எட்டு ஏழு பூஜ்யம்",
    "காலை பத்து மணி முப்பது நிமிடம் ஐந்து புள்ளி ஐந்து கிலோ அரிசி",
    "இரண்டாயிரத்து இருபத்துநான்கில் நான்கில் மூன்று பங்கு மக்கள் இருபத்தைந்து சதவீதம் வளர்ச்சி",
]
REPEATS = 20


def _peak_mb() -> float:
    """
    Peak resident set size of this process in MiB.
    """
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def build(direction: str, cache_dir: str) -> None:
    """
    Compile one direction from scratch and report time, peak memory and FAR size.
    """
    start = time.perf_counter()
    if direction == "tn":
        Normalizer(cache_dir=cache_dir, overwrite_cache=True)
    else:
        InverseNormalizer(cache_dir=cache_dir, overwrite_cache=True)
    far = far_path(cache_dir, "ta", direction)
    print(
        f"{direction}\tbuild={time.perf_counter() - start:.1f}s"
        f"\tpeak={_peak_mb():.0f}MB\tfar={far.stat().st_size / 1024 / 1024:.0f}MB"
    )


def _bench(label: str, normalize: Callable[[str], str], samples: list[str]) -> None:
    """
    Report the median of ``REPEATS`` timed runs per sample, after one warm-up.
    """
    print(f"\n[{label}]")
    medians = []
    for text in samples:
        normalize(text)
        times = []
        for _ in range(REPEATS):
            start = time.perf_counter()
            normalize(text)
            times.append((time.perf_counter() - start) * 1000)
        medians.append(statistics.median(times))
        print(
            f"  {len(text):>3} chars  median {medians[-1]:7.1f} ms"
            f"  min {min(times):7.1f}  max {max(times):7.1f}  | {text[:44]}"
        )
    print(f"  total median across samples: {sum(medians):.0f} ms")


def measure(cache_dir: str) -> None:
    """
    Load both directions from the FAR cache and time the pinned samples.
    """
    start = time.perf_counter()
    tn = Normalizer(cache_dir=cache_dir)
    tn_load = time.perf_counter() - start
    start = time.perf_counter()
    itn = InverseNormalizer(cache_dir=cache_dir)
    itn_load = time.perf_counter() - start
    print(f"load\ttn={tn_load:.2f}s\titn={itn_load:.2f}s\trss={_peak_mb():.0f}MB")
    _bench("TN written -> spoken", tn.normalize, TN_SAMPLES)
    _bench("ITN spoken -> written", itn.inverse_normalize, ITN_SAMPLES)


def main() -> None:
    """
    Run the requested measurement.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["build", "measure"])
    parser.add_argument("direction", nargs="?", choices=["tn", "itn"])
    parser.add_argument("--cache-dir", required=True)
    args = parser.parse_args()

    logging.disable(logging.WARNING)
    if args.mode == "build":
        if args.direction is None:
            parser.error("build needs a direction")
        build(args.direction, args.cache_dir)
    else:
        measure(args.cache_dir)


if __name__ == "__main__":
    main()
