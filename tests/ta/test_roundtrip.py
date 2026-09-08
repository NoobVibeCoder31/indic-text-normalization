"""
Round-trip census: the spoken form TN emits must inverse-normalize back to the input.
"""

from indic_text_normalization import InverseNormalizer, Normalizer


def _census() -> list[int]:
    """
    Every shape the number sandhi can take, plus strided samples of the larger scales.
    """
    numbers = list(range(0, 200))
    numbers += [tens * 10 + digit for tens in range(2, 10) for digit in range(10)]
    numbers += [hundreds * 100 + digit for hundreds in range(1, 10) for digit in range(10)]
    numbers += list(range(1000, 10000, 37))
    numbers += list(range(10000, 100000, 997))
    numbers += list(range(100000, 100000000, 3999983))
    return sorted(set(numbers))


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
