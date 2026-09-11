"""
Unit tests for the shared FST helpers.
"""

import pynini
import pytest
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import sequential


def _explored(text: str, fst: pynini.Fst) -> int:
    """
    States the composition visits before trimming, i.e. its real cost.
    """
    return int(pynini.compose(pynini.escape(text), fst, connect=False).num_states())


class TestSequential:
    """
    ``sequential`` keeps the relation of an inverted grammar but reads it input-first.
    """

    @pytest.fixture
    def inverted(self) -> pynini.Fst:
        # A toy TN number grammar (digits -> words) inverted for ITN, the way the ITN
        # cardinal taggers are built: the deleted zero becomes an eps-input arc that
        # emits a digit before any input is read.
        digit = pynini.string_map([("1", "one"), ("2", "two")])
        tens = digit + pynutil.delete("0") + pynutil.insert("ty")
        return pynini.invert(digit | tens).optimize()

    def test_relation_is_unchanged(self, inverted: pynini.Fst) -> None:
        """
        Every spoken form maps to the same digits before and after.
        """
        seq = sequential(inverted)
        for spoken, written in [("one", "1"), ("two", "2"), ("onety", "10"), ("twoty", "20")]:
            assert pynini.shortestpath(pynini.escape(spoken) @ seq).string() == written
            assert pynini.shortestpath(pynini.escape(spoken) @ inverted).string() == written
        assert (pynini.escape("three") @ seq).num_states() == 0

    def test_composition_explores_less(self, inverted: pynini.Fst) -> None:
        """
        A word outside the grammar dies after its first byte instead of visiting every
        digit prefix the grammar can emit.
        """
        assert _explored("x", sequential(inverted)) < _explored("x", inverted)

    def test_keeps_alternatives_and_weights(self) -> None:
        """
        Two readings of one input survive with their weights, so the best still wins.
        """
        fst = pynini.union(pynini.cross("a", "1"), pynutil.add_weight(pynini.cross("a", "2"), 1.0))
        seq = sequential(fst.optimize())
        assert pynini.shortestpath(pynini.escape("a") @ seq).string() == "1"
        assert sorted(seq.paths().ostrings()) == ["1", "2"]

    def test_rejects_cyclic_input(self) -> None:
        """
        A cyclic transducer may not determinize, so it is refused rather than hang.
        """
        with pytest.raises(ValueError, match="acyclic"):
            sequential(pynini.closure(pynini.cross("a", "b")))
