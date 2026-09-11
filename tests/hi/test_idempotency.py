"""
Idempotency and round-trip tests for the Hindi grammars.
"""

import random
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from indic_text_normalization import InverseNormalizer, Normalizer

DATA_DIR = Path(__file__).parent.parent / "data" / "hi"

# Spoken outputs that are themselves re-tagged. These document known non-idempotent forms.
KNOWN_TN_FAILURES: set[str] = set()
KNOWN_ITN_FAILURES: set[str] = set()
# Written forms whose spoken reading keeps a word ITN deliberately leaves alone
# (से for a range, प्रतिशत for a percentage, बराबर for "="), so TN followed by ITN
# cannot restore them.
ROUND_TRIP_EXEMPT = {"10-20", "12.5%", "5 = 5", "a = b"}
# A bare एक is as often the article "a" as the numeral, so ITN leaves it alone.
ROUND_TRIP_SKIP_INTEGERS = {1}

# Spoken symbols glued to digits, letters, currency or each other.
_SYMBOL_ATOMS = [
    "5",
    "५",
    "अ",
    "₹",
    "%",
    "#",
    "+",
    "*",
    "&",
    "<",
    ">",
    "^",
    "(",
    ")",
    "/",
    "-",
    "@",
    "_",
    '"',
    "[",
    "]",
]
_SYMBOL_PAIRS = {a + b for a in _SYMBOL_ATOMS for b in _SYMBOL_ATOMS} | {
    a + " " + b for a in _SYMBOL_ATOMS for b in _SYMBOL_ATOMS
}

# Hindi letters U+0C05-U+0C39, vowel signs U+0C3E-U+0C4D, digits U+0C66-U+0C6F, ZWJ/ZWNJ,
# plus every ASCII symbol the grammars speak.
_HINDI_ALPHABET = (
    [chr(i) for i in range(0x0C05, 0x0C3A)]
    + [chr(i) for i in range(0x0C3E, 0x0C4E)]
    + [chr(i) for i in range(0x0C66, 0x0C70)]
    + ["‌", "‍"]
    + list(' .,-:0123456789%₹/#+*&<>^()[]"')
)


# Round-trip shapes: every units word, every tens row with a unit and a teen, each hundreds
# form with a zero, unit, teen and tens remainder, and every scale word in its exact and
# oblique form next to every remainder type. The exhaustive sweep lives in
# ``benchmarks/roundtrip_census.py``.
_BELOW_HUNDRED = [*range(0, 20), *[t * 10 + u for t in range(2, 10) for u in (0, 1, 5, 9)]]
_HUNDREDS = [h * 100 + r for h in range(1, 10) for r in (0, 1, 5, 10, 11, 19, 50, 99)]
_SCALES = [
    1000, 1001, 1010, 1100, 1101, 1105, 1110, 1500, 1999, 2000, 2001, 2010, 2022, 2100, 2222,
    9999, 10000, 10001, 10100, 10500, 11000, 12345, 22222, 50000, 99999, 100000, 100001,
    100100, 101000, 110000, 150000, 200000, 200001, 222222, 999999, 1000000, 1000001,
    2500000, 9999999, 10000000, 10000001, 10100000, 11000000, 15000000, 20000000, 22222222,
    99999999, 100000000, 123456789, 222222222, 999999999,
]  # fmt: skip
ROUND_TRIP_NUMBERS = [*_BELOW_HUNDRED, *_HUNDREDS, *_SCALES]


def _golden_outputs(direction: str) -> list[str]:
    outputs = []
    for path in sorted((DATA_DIR / direction).glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                outputs.extend(line.split("~")[1:])
    return outputs


def _golden_inputs(direction: str) -> list[str]:
    inputs = []
    for path in sorted((DATA_DIR / direction).glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                inputs.append(line.split("~")[0])
    return inputs


class TestIdempotency:
    """
    normalize(normalize(x)) == normalize(x) over golden outputs and random text.
    """

    @pytest.mark.parametrize("spoken", sorted(set(_golden_outputs("tn"))))
    def test_tn_golden_outputs_stable(self, hi_tn: Normalizer, spoken: str) -> None:
        """
        Every TN golden output passes through TN unchanged.
        """
        if spoken in KNOWN_TN_FAILURES:
            pytest.xfail("documented non-idempotent form")
        assert hi_tn.normalize(spoken) == spoken

    @pytest.mark.parametrize("written", sorted(set(_golden_outputs("itn"))))
    def test_itn_golden_outputs_stable(self, hi_itn: InverseNormalizer, written: str) -> None:
        """
        Every ITN golden output passes through ITN unchanged.
        """
        if written in KNOWN_ITN_FAILURES:
            pytest.xfail("documented non-idempotent form")
        assert hi_itn.inverse_normalize(written) == written

    @pytest.mark.parametrize("text", sorted(_SYMBOL_PAIRS))
    def test_tn_symbol_pairs_idempotent(self, hi_tn: Normalizer, text: str) -> None:
        """
        Every digit/letter/symbol pair (glued or spaced) is a TN fixed point after one pass.
        """
        once = hi_tn.normalize(text)
        assert hi_tn.normalize(once) == once

    @given(text=st.text(alphabet=_HINDI_ALPHABET, max_size=30))
    @settings(
        max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_tn_random_idempotent(self, hi_tn: Normalizer, text: str) -> None:
        """
        TN is idempotent over random Hindi-and-digit strings.
        """
        once = hi_tn.normalize(text)
        assert hi_tn.normalize(once) == once

    @given(text=st.text(alphabet=_HINDI_ALPHABET, max_size=30))
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_itn_random_idempotent(self, hi_itn: InverseNormalizer, text: str) -> None:
        """
        ITN is idempotent over random Hindi-and-digit strings.
        """
        once = hi_itn.inverse_normalize(text)
        assert hi_itn.inverse_normalize(once) == once


class TestRoundTrip:
    """
    Numbers survive TN followed by ITN, and no golden input triggers a silent fallback.
    """

    def test_integers_round_trip(self, hi_tn: Normalizer, hi_itn: InverseNormalizer) -> None:
        """
        Every structural number shape plus a small seeded sample per magnitude round-trips.
        """
        rng = random.Random(20260907)  # noqa: S311
        numbers = ROUND_TRIP_NUMBERS + [
            rng.randrange(10**k, 10 ** (k + 1)) for k in range(3, 9) for _ in range(10)
        ]
        failures = [
            (n, spoken, back)
            for n in numbers
            if n not in ROUND_TRIP_SKIP_INTEGERS
            for spoken in [hi_tn.normalize(str(n))]
            for back in [hi_itn.inverse_normalize(spoken)]
            if back != str(n)
        ]
        assert failures[:20] == []

    @pytest.mark.parametrize("written", sorted(set(_golden_outputs("itn"))))
    def test_itn_outputs_survive_tn(
        self, hi_tn: Normalizer, hi_itn: InverseNormalizer, written: str
    ) -> None:
        """
        ITN golden outputs re-verbalize and inverse-normalize back to themselves.
        """
        if written in ROUND_TRIP_EXEMPT:
            pytest.skip("spoken form keeps a word ITN leaves alone")
        spoken = hi_tn.normalize(written)
        assert hi_itn.inverse_normalize(spoken) == written

    @pytest.mark.parametrize("text", sorted(set(_golden_inputs("tn"))))
    def test_tn_no_silent_fallback(
        self, hi_tn: Normalizer, text: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        No golden TN input is returned unchanged because tagging or verbalization failed.
        """
        with caplog.at_level("WARNING", logger="indic_text_normalization.core.engine"):
            hi_tn.normalize(text)
        assert not [
            r for r in caplog.records if "Failed" in r.message or "No verbalization" in r.message
        ]

    @pytest.mark.parametrize("text", sorted(set(_golden_inputs("itn"))))
    def test_itn_no_silent_fallback(
        self, hi_itn: InverseNormalizer, text: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        No golden ITN input is returned unchanged because tagging or verbalization failed.
        """
        with caplog.at_level("WARNING", logger="indic_text_normalization.core.engine"):
            hi_itn.inverse_normalize(text)
        assert not [
            r for r in caplog.records if "Failed" in r.message or "No verbalization" in r.message
        ]
