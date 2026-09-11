"""
Engine-level regression tests: verbalization cost, pre-cleaning and output spacing.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pynini
import pytest

from indic_text_normalization import Normalizer
from indic_text_normalization.core.engine import NormalizationEngine

ENGINE_LOGGER = "indic_text_normalization.core.engine"


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

    def test_many_money_tokens_verbalize_in_linear_time_telugu(self, te_tn: Normalizer) -> None:
        """
        The Telugu money verbalizer is also linear in the number of tokens.
        """
        text = " ".join(["₹5"] * 20)
        start = time.perf_counter()
        output = te_tn.normalize(text)
        assert time.perf_counter() - start < 10
        assert output == " ".join(["ఐదు రూపాయలు"] * 20)

    def test_multi_word_units_use_plain_spaces_telugu(self, te_tn: Normalizer) -> None:
        """
        Multi-word Telugu units and symbols must not leak U+00A0 NO-BREAK SPACE.
        """
        for text in ["5cm2", "-40°C", "→", "5 → 10", "™"]:
            output = te_tn.normalize(text)
            assert "\u00a0" not in output
            assert te_tn.normalize(output) == output

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


class TestFailureLogging:
    """
    A failure names its shape, never the caller's text: inputs are phone numbers and money.
    """

    PHONE = "9876543210"

    def test_tagging_failure_logs_only_metadata(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        An untaggable input warns with a length and an exception type, not the text.
        """
        engine = NormalizationEngine(pynini.accep("zzz"), pynini.accep("zzz"))
        with caplog.at_level(logging.WARNING, logger=ENGINE_LOGGER):
            assert engine.normalize(self.PHONE) == self.PHONE
        assert caplog.records
        assert all(self.PHONE not in r.getMessage() for r in caplog.records)
        assert "10 chars" in caplog.records[0].getMessage()

    def test_payload_is_logged_only_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        The text reaches the log only when the caller opts in by enabling DEBUG.
        """
        engine = NormalizationEngine(pynini.accep("zzz"), pynini.accep("zzz"))
        with caplog.at_level(logging.DEBUG, logger=ENGINE_LOGGER):
            engine.normalize(self.PHONE)
        by_level: dict[int, list[str]] = {logging.DEBUG: [], logging.WARNING: []}
        for record in caplog.records:
            by_level.setdefault(record.levelno, []).append(record.getMessage())
        assert any(self.PHONE in message for message in by_level[logging.DEBUG])
        assert by_level[logging.WARNING]
        assert all(self.PHONE not in message for message in by_level[logging.WARNING])

    def test_missing_verbalization_logs_the_class_not_the_value(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        An unverbalizable token warns with its semiotic class, not the tagged value.
        """
        tagged = f'tokens {{ cardinal {{ integer: "{self.PHONE}" }} }}'
        engine = NormalizationEngine(pynini.cross(self.PHONE, tagged), pynini.accep("unrelated"))
        with caplog.at_level(logging.WARNING, logger=ENGINE_LOGGER):
            assert engine.normalize(self.PHONE) == self.PHONE
        assert caplog.records
        message = caplog.records[0].getMessage()
        assert "cardinal" in message
        assert self.PHONE not in message
