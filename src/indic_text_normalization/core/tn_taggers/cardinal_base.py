"""
The interface a language's TN cardinal tagger presents to the shared taggers, plus the
digit-grouping helpers every number grammar needs.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import GraphFst
from indic_text_normalization.core.profile import LanguageProfile


def delete_commas(any_digit: pynini.Fst) -> pynini.Fst:
    """
    Digit run with optional single commas between digits, commas deleted.
    """
    return (
        any_digit + pynini.closure(pynini.closure(pynutil.delete(","), 0, 1) + any_digit)
    ).optimize()


def indian_comma_pattern(any_digit: pynini.Fst) -> pynini.Fst:
    """
    Acceptor for the Indian grouping 12,34,567 (2-digit groups, a final 3-digit group).
    """
    comma = pynini.accep(",")
    return (
        pynini.closure(any_digit, 1, 2)
        + pynini.closure(comma + any_digit + any_digit, 1)
        + pynini.closure(comma + any_digit + any_digit + any_digit, 0, 1)
    ).optimize()


def intl_comma_pattern(any_digit: pynini.Fst) -> pynini.Fst:
    """
    Acceptor for the international grouping 1,234,567 (3-digit groups).
    """
    comma = pynini.accep(",")
    return (
        pynini.closure(any_digit, 1, 3)
        + pynini.closure(comma + any_digit + any_digit + any_digit, 1)
    ).optimize()


class CardinalBase(GraphFst):
    """
    Base class for a language's TN cardinal tagger.

    The shared date, decimal, fraction, measure, money, ordinal, range, telephone and
    ITN taggers only use what is declared here, so a language adds a number system by
    subclassing this and filling the attributes in ``__init__``.

    Attributes
    ----------
    profile : ``LanguageProfile``
        The language's profile.
    final_graph : ``pynini.Fst``
        Digits in either script, optionally comma-grouped, to the spoken number.
    itn_input_graph : ``pynini.Fst``
        ``final_graph`` with TN's own preference weights removed, for inversion by ITN.
    digit_by_digit : ``pynini.Fst``
        Two or more digits read one at a time (007, numbers beyond the grammar's range).
    digit : ``pynini.Fst``
        Native non-zero digit to its word.
    zero : ``pynini.Fst``
        Native zero digit to its word.
    graph_year_hundreds : ``pynini.Fst | None``
        Years 1100-1999 read as hundreds (పందొమ్మిది వందల నలభై ఏడు), or None when the
        language reads years as plain numbers.
    ordinal_tails : ``tuple[str, ...]``
        Inflected tails an ordinal may carry after its marker, ``""`` included.
    known_suffixes : ``pynini.Fst``
        Every case or ordinal suffix that may be written glued to a digit; anything else
        glued to a digit is split off as a separate word by the tokenizer.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(self, profile: LanguageProfile, deterministic: bool = True) -> None:
        super().__init__(name="cardinal", kind="classify", deterministic=deterministic)
        self.profile = profile
        self.final_graph: pynini.Fst
        self.itn_input_graph: pynini.Fst
        self.digit_by_digit: pynini.Fst
        self.digit: pynini.Fst
        self.zero: pynini.Fst
        self.graph_year_hundreds: pynini.Fst | None = None
        self.ordinal_tails: tuple[str, ...] = ("",)
        self.known_suffixes: pynini.Fst

    def attach_case_suffix(self, graph: pynini.Fst, include_vowel: bool = True) -> pynini.Fst:
        """
        Accept a written case suffix after ``graph`` and attach it to the last spoken word.

        Parameters
        ----------
        graph : ``pynini.Fst``
            A digits-to-words transducer.
        include_vowel : ``bool``, optional (default = True)
            If False, leave out suffixes that are a bare vowel sign.
        """
        raise NotImplementedError

    def ordinal_graph(self, graph: pynini.Fst) -> pynini.Fst:
        """
        Read ``graph`` followed by the written ordinal marker and an optional tail.
        """
        raise NotImplementedError

    def readable_years(self) -> pynini.Fst:
        """
        Every reading of a number ITN should invert: the cardinal plus the hundreds-style years.
        """
        if self.graph_year_hundreds is None:
            return self.final_graph
        return pynini.union(self.final_graph, self.graph_year_hundreds).optimize()
