# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
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
Tag-and-verbalize pipeline shared by all languages and both directions.
"""

import itertools
import logging
import re
import unicodedata
from collections.abc import Iterator

import pynini

from indic_text_normalization.core.token_parser import PRESERVE_ORDER_KEY, Token, TokenParser

logger = logging.getLogger(__name__)

_SPACE_DUP = re.compile(r" {2,}")

# Zero-width/format characters with no linguistic role (ZWJ/ZWNJ are preserved),
# dash lookalikes, and exotic spaces, normalized before tagging.
_PRE_CLEAN = str.maketrans(
    {
        "​": None,  # ZERO WIDTH SPACE
        "﻿": None,  # BOM / ZERO WIDTH NO-BREAK SPACE
        "⁠": None,  # WORD JOINER
        "–": "-",  # EN DASH
        "—": "-",  # EM DASH
        "−": "-",  # MINUS SIGN
        " ": " ",  # THIN SPACE
        " ": " ",  # HAIR SPACE
        " ": " ",  # NARROW NO-BREAK SPACE
    }
)


class NormalizationEngine:
    """
    Run text through a classify FST and a verbalize FST.

    Attributes
    ----------
    classify : ``pynini.Fst``
        Tagger grammar producing tagged token strings.
    verbalize : ``pynini.Fst``
        Verbalizer grammar consuming tagged token strings.
    """

    def __init__(self, classify: pynini.Fst, verbalize: pynini.Fst) -> None:
        self.classify = classify
        self.verbalize = verbalize
        self.parser = TokenParser()

    def normalize(self, text: str) -> str:
        """
        Transduce ``text`` through the tagger and verbalizer.

        Returns the input unchanged when it is empty or cannot be transduced.
        """
        text = unicodedata.normalize("NFC", text).translate(_PRE_CLEAN)
        text = _SPACE_DUP.sub(" ", text.strip())
        if not text:
            return text
        escaped = pynini.escape(text)
        try:
            tagged_lattice = escaped @ self.classify
            tagged_text = pynini.shortestpath(tagged_lattice, nshortest=1, unique=True).string()
        except Exception:
            logger.warning("Failed to tag text: %s", text)
            return text

        self.parser(tagged_text)
        tokens = self.parser.parse()
        try:
            output = self._verbalize(tokens, tagged_text)
        except Exception:
            logger.warning("Failed to verbalize text: %s", text)
            return text
        if output is None:
            return text
        return _SPACE_DUP.sub(" ", output).strip()

    def _verbalize(self, tokens: list[Token], tagged_text: str) -> str | None:
        """
        Find the first token permutation the verbalizer accepts.
        """
        for candidate in self._generate_permutations(tokens):
            lattice = pynini.escape(candidate) @ self.verbalize
            if lattice.num_states() != 0:
                path: str = pynini.shortestpath(lattice, nshortest=1, unique=True).string()
                return path
        logger.warning("No verbalization found for: %s", tagged_text)
        return None

    def _permute(self, d: Token) -> list[str]:
        """
        Serialize a token dictionary in every field order the verbalizer may accept.
        """
        results = []
        perms = [list(d.items())] if PRESERVE_ORDER_KEY in d else itertools.permutations(d.items())
        for perm in perms:
            subl = [""]
            for k, v in perm:
                if isinstance(v, str):
                    piece = f'{k}: "{v}" ' if k != PRESERVE_ORDER_KEY else f"{k}: true "
                    subl = ["".join(x) for x in itertools.product(subl, [piece])]
                else:
                    rec = self._permute(v)
                    subl = [
                        "".join(x) for x in itertools.product(subl, [f" {k} {{ "], rec, [" } "])
                    ]
            results.extend(subl)
        return results

    def _generate_permutations(self, tokens: list[Token]) -> Iterator[str]:
        """
        Yield serialized permutations of the token list, depth first.
        """

        def _helper(prefix: str, idx: int) -> Iterator[str]:
            if idx == len(tokens):
                yield prefix
                return
            for option in self._permute(tokens[idx]):
                yield from _helper(prefix + option, idx + 1)

        return _helper("", 0)
