"""
Round-trip census: the spoken form TN emits must inverse-normalize back to the input.
"""

from indic_text_normalization import InverseNormalizer, Normalizer


def _census() -> list[int]:
    """
    Every integer below 1200 (all tens/hundreds sandhi shapes) plus strided samples.
    """
    numbers = list(range(0, 1200))
    numbers += list(range(1200, 100000, 101))
    numbers += list(range(100000, 100000000, 999983))
    return numbers


class TestRoundTrip:
    """
    ``inverse_normalize(normalize(n)) == n`` over a census of integers.
    """

    def test_integers(self, ta_tn: Normalizer, ta_itn: InverseNormalizer) -> None:
        """
        No integer in the census loses its value through TN followed by ITN.
        """
        failures = []
        for number in _census():
            written = str(number)
            spoken = ta_tn.normalize(written)
            if ta_itn.inverse_normalize(spoken) != written:
                failures.append((written, spoken, ta_itn.inverse_normalize(spoken)))
        assert not failures, f"{len(failures)} of {len(_census())} failed: {failures[:15]}"
