"""
Engine-level regression tests: verbalization cost, pre-cleaning and output spacing.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from indic_text_normalization import Normalizer


class TestEngine:
    """
    Behaviour of the shared tag-and-verbalize engine on the Tamil TN grammar.
    """

    def test_many_money_tokens_verbalize_in_linear_time(self, ta_tn: Normalizer) -> None:
        """
        Twenty money tokens in one sentence must not explode into field permutations.
        """
        text = " ".join(["₹5"] * 20)
        start = time.perf_counter()
        output = ta_tn.normalize(text)
        assert time.perf_counter() - start < 10
        assert output == " ".join(["ஐந்து ரூபாய்"] * 20)

    def test_multi_word_symbols_use_plain_spaces(self, ta_tn: Normalizer) -> None:
        """
        Multi-word whitelist values must not leak U+00A0 NO-BREAK SPACE into the output.
        """
        for text in ["→", "™", "5 → 10"]:
            output = ta_tn.normalize(text)
            assert " " not in output
            assert ta_tn.normalize(output) == output

    def test_normalize_is_thread_safe(self, ta_tn: Normalizer) -> None:
        """
        Concurrent normalize() calls on one instance must not corrupt each other.
        """
        cases = {
            "5 65 மற்றும் 70": "ஐந்து அறுபத்தைந்து மற்றும் எழுபது",
            "₹1,250.50": "ஆயிரத்து இருநூற்று ஐம்பது ரூபாய் ஐம்பது பைசா",
            "15-06-2024": "பதினைந்து ஜூன் இரண்டாயிரத்து இருபத்துநான்கு",
        }
        items = list(cases.items())
        # A timeout so one worker's assertion failure breaks the barrier and every
        # other worker exits, instead of the suite hanging on the next round.
        barrier = threading.Barrier(8, timeout=30)

        def work(i: int) -> None:
            for round_ in range(50):
                barrier.wait()
                text, expected = items[(i + round_) % len(items)]
                assert ta_tn.normalize(text) == expected

        with ThreadPoolExecutor(max_workers=8) as pool:
            for future in [pool.submit(work, i) for i in range(8)]:
                future.result()

    def test_zero_width_characters(self, ta_tn: Normalizer) -> None:
        """
        Zero-width space between digits is a boundary; bidi marks and soft hyphens vanish.
        """
        assert ta_tn.normalize("5​6") == "ஐந்து ஆறு"
        assert ta_tn.normalize("5⁠6") == "ஐந்து ஆறு"
        assert ta_tn.normalize("5.5‎") == "ஐந்து புள்ளி ஐந்து"
        assert ta_tn.normalize("‏5") == "ஐந்து"
        assert ta_tn.normalize("5­0") == "ஐம்பது"
        assert ta_tn.normalize("5‌6") == "5‌6"
