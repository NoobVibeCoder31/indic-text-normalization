"""
Idempotency tests: normalizing already-normalized text must be a no-op.
"""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from indic_text_normalization import InverseNormalizer, Normalizer

DATA_DIR = Path(__file__).parent.parent / "data" / "ta"

# Spoken outputs that are themselves re-tagged (e.g. a bare number word is a
# valid ITN/ordinal input). These document known non-idempotent forms.
KNOWN_TN_FAILURES: set[str] = set()

_TAMIL_ALPHABET = [chr(i) for i in range(0x0B85, 0x0BB9)] + list(" .,-:0123456789")


def _golden_outputs(direction: str) -> list[str]:
    outputs = []
    for path in sorted((DATA_DIR / direction).glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                outputs.extend(line.split("~")[1:])
    return outputs


class TestIdempotency:
    """
    normalize(normalize(x)) == normalize(x) over golden outputs and random text.
    """

    @pytest.mark.parametrize("spoken", sorted(set(_golden_outputs("tn"))))
    def test_tn_golden_outputs_stable(self, ta_tn: Normalizer, spoken: str) -> None:
        """
        Every TN golden output passes through TN unchanged.
        """
        if spoken in KNOWN_TN_FAILURES:
            pytest.xfail("documented non-idempotent form")
        assert ta_tn.normalize(spoken) == spoken

    @given(text=st.text(alphabet=_TAMIL_ALPHABET, max_size=30))
    @settings(
        max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_tn_random_idempotent(self, ta_tn: Normalizer, text: str) -> None:
        """
        TN is idempotent over random Tamil-and-digit strings.
        """
        once = ta_tn.normalize(text)
        assert ta_tn.normalize(once) == once

    @given(text=st.text(alphabet=_TAMIL_ALPHABET, max_size=30))
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_itn_random_idempotent(self, ta_itn: InverseNormalizer, text: str) -> None:
        """
        ITN is idempotent over random Tamil-and-digit strings.
        """
        once = ta_itn.inverse_normalize(text)
        assert ta_itn.inverse_normalize(once) == once
