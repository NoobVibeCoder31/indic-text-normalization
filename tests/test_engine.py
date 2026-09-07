"""
Engine-level regression tests: verbalization cost, pre-cleaning and output spacing.
"""

import time

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
