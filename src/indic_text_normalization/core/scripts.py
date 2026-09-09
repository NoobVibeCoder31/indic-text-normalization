"""
Digit FST builders shared by all Indic script packages.
"""

from dataclasses import dataclass

import pynini


@dataclass(frozen=True)
class ScriptDigitFsts:
    """
    Digit FSTs for one Indic script.

    Attributes
    ----------
    digit : ``pynini.Fst``
        Acceptor for the ten native digits.
    non_zero : ``pynini.Fst``
        Acceptor for the nine non-zero native digits.
    to_ascii : ``pynini.Fst``
        Transducer from native digits to ASCII digits.
    from_ascii : ``pynini.Fst``
        Transducer from ASCII digits to native digits.
    zero : ``str``
        The native zero character.
    """

    digit: pynini.Fst
    non_zero: pynini.Fst
    to_ascii: pynini.Fst
    from_ascii: pynini.Fst
    zero: str


def script_digit_fsts(block_start: str) -> ScriptDigitFsts:
    """
    Build digit FSTs for a script whose zero is ``block_start``.

    Parameters
    ----------
    block_start : ``str``
        The script's zero character, e.g. U+0BE6 TAMIL DIGIT ZERO. Indic digit
        blocks are contiguous, so the remaining digits are derived by offset.

    Returns
    -------
    ``ScriptDigitFsts``
        The digit FST bundle for the script.
    """
    zero = ord(block_start)
    natives = [chr(zero + i) for i in range(10)]
    pairs = [(str(i), natives[i]) for i in range(10)]
    return ScriptDigitFsts(
        digit=pynini.union(*natives).optimize(),
        non_zero=pynini.union(*natives[1:]).optimize(),
        to_ascii=pynini.string_map([(n, a) for a, n in pairs]).optimize(),
        from_ascii=pynini.string_map(pairs).optimize(),
        zero=natives[0],
    )
