# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
# Copyright 2015 and onwards Google, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Script-agnostic FST building blocks shared by every language package.
"""

import logging
import string
import sys
from functools import cache
from unicodedata import category

import pynini
from pynini.export import export
from pynini.lib import byte, pynutil, utf8

CHAR = utf8.VALID_UTF8_CHAR
DIGIT = byte.DIGIT
LOWER = pynini.union(*string.ascii_lowercase).optimize()
UPPER = pynini.union(*string.ascii_uppercase).optimize()
ALPHA = pynini.union(LOWER, UPPER).optimize()

NON_BREAKING_SPACE = "\u00a0"  # U+00A0 NO-BREAK SPACE, the joiner inside a token value
SPACE = " "
WHITE_SPACE = pynini.union(" ", "\t", "\n", "\r", "\u00a0").optimize()
NOT_SPACE = pynini.difference(CHAR, WHITE_SPACE).optimize()
NOT_QUOTE = pynini.difference(CHAR, r'"').optimize()
SIGMA = pynini.closure(CHAR)

TO_LOWER = pynini.union(
    *[
        pynini.cross(x, y)
        for x, y in zip(string.ascii_uppercase, string.ascii_lowercase, strict=True)
    ]
)
TO_UPPER = pynini.invert(TO_LOWER)

delete_space = pynutil.delete(pynini.closure(WHITE_SPACE))
delete_zero_or_one_space = pynutil.delete(pynini.closure(WHITE_SPACE, 0, 1))
insert_space = pynutil.insert(" ")
delete_extra_space = pynini.cross(pynini.closure(WHITE_SPACE, 1), " ")
delete_preserve_order = pynini.closure(
    pynutil.delete(" preserve_order: true")
    | (pynutil.delete(' field_order: "') + NOT_QUOTE + pynutil.delete('"'))
)


@cache
def punctuation_code_points() -> list[str]:
    """
    Every Unicode punctuation code point, computed once per process on first use.

    The scan is ~1.1 M category lookups, so it is deferred: a process that only loads a
    compiled grammar from the FAR cache never pays for it.
    """
    return [chr(i) for i in range(sys.maxunicode + 1) if category(chr(i)).startswith("P")]


# Currency symbols the money grammars read; also what may precede a re-fed written amount.
CURRENCY_SYMBOLS = "₹$£€¥₩₺৳₦"

MIN_NEG_WEIGHT = -0.0001
MIN_POS_WEIGHT = 0.0001


def rank(weight: float) -> pynini.Fst:
    """
    A weight-carrying epsilon for the tail of a union branch: at the head the same weight
    would keep the branch's prefix from merging with its neighbours'.
    """
    return pynutil.insert("", weight)


def unweighted(fst: pynini.Fst) -> pynini.Fst:
    """
    Drop every arc weight, leaving only the consuming grammar's own weights to rank paths.
    """
    return pynini.arcmap(fst.optimize(), map_type="rmweight").optimize()


def sequential(fst: pynini.Fst) -> pynini.Fst:
    """
    Input-deterministic form of an acyclic transducer, for grammars that read spoken words.

    An inverted TN grammar emits its digits *before* consuming any input (the TN side
    deleted them), so composing a string with it explores the whole digit skeleton at
    every word start, in every tagger that embeds it. Determinizing on the input delays
    each output until the input that decides it has been read, so composition explores
    one path per input prefix. The language, outputs and weights are unchanged.

    Parameters
    ----------
    fst : ``pynini.Fst``
        An acyclic transducer; several outputs for one input are kept as alternatives.

    Returns
    -------
    ``pynini.Fst``
        The optimized input-deterministic transducer.

    Raises
    ------
    ``ValueError``
        If ``fst`` is cyclic, because determinization may then not terminate.
    """
    acyclic = pynini.ACYCLIC  # type: ignore[attr-defined]
    if fst.properties(acyclic, True) != acyclic:
        raise ValueError("sequential() needs an acyclic transducer.")
    return pynini.determinize(fst, det_type="nonfunctional").optimize()


def generator_main(file_name: str, graphs: dict[str, pynini.Fst]) -> None:
    """
    Export graphs as an OpenFst finite state archive (FAR) file.

    Parameters
    ----------
    file_name : ``str``
        Path of the FAR file to create.
    graphs : ``dict[str, pynini.Fst]``
        Mapping of rule name to the pynini WFST graph to export.
    """
    exporter = export.Exporter(file_name)
    for rule, graph in graphs.items():
        # Callers own optimization; re-optimizing here repeats it on the whole grammar.
        exporter[rule] = graph
    exporter.close()
    logging.info("Created %s", file_name)


def convert_space(fst: pynini.Fst) -> pynini.Fst:
    """
    Convert breaking spaces to non-breaking spaces inside quoted token values.
    """
    return fst @ pynini.cdrewrite(pynini.cross(SPACE, NON_BREAKING_SPACE), "", "", SIGMA)


class GraphFst:
    """
    Base class for all grammar FSTs.

    Attributes
    ----------
    name : ``str``
        Name of the grammar class, used as the token tag (e.g. ``cardinal``).
    kind : ``str``
        Either ``classify`` (tagger) or ``verbalize`` (verbalizer).
    deterministic : ``bool``, optional (default = True)
        If True the grammar provides a single transduction option.
    """

    def __init__(self, name: str, kind: str, deterministic: bool = True) -> None:
        self.name = name
        self.kind = kind
        self.deterministic = deterministic
        self._fst: pynini.Fst | None = None

    @property
    def fst(self) -> pynini.Fst:
        if self._fst is None:
            raise ValueError(f"FST for grammar {self.name!r} ({self.kind}) has not been built.")
        return self._fst

    @fst.setter
    def fst(self, fst: pynini.Fst) -> None:
        self._fst = fst

    def add_tokens(self, fst: pynini.Fst) -> pynini.Fst:
        """
        Wrap the class name around the given tagger fst.
        """
        return pynutil.insert(f"{self.name} {{ ") + fst + pynutil.insert(" }")

    def delete_tokens(self, fst: pynini.Fst) -> pynini.Fst:
        """
        Delete the class name wrapper around the given verbalizer fst.
        """
        res = (
            pynutil.delete(f"{self.name}")
            + delete_space
            + pynutil.delete("{")
            + delete_space
            + fst
            + delete_space
            + pynutil.delete("}")
        )
        return res @ pynini.cdrewrite(pynini.cross("\u00a0", " "), "", "", SIGMA)
