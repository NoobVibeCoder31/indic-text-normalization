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

import pynini

from indic_text_normalization.core.token_parser import PRESERVE_ORDER_KEY, Token, TokenParser

logger = logging.getLogger(__name__)

_SPACE_DUP = re.compile(r" {2,}")

# Zero-width/format characters with no linguistic role (ZWJ/ZWNJ are preserved),
# dash lookalikes, and exotic spaces, normalized before tagging.
_PRE_CLEAN = str.maketrans(
    {
        "\u200b": None,  # ZERO WIDTH SPACE
        "\ufeff": None,  # ZERO WIDTH NO-BREAK SPACE (BOM)
        "\u2060": None,  # WORD JOINER
        "\u00ad": None,  # SOFT HYPHEN
        "\u200e": None,  # LEFT-TO-RIGHT MARK
        "\u200f": None,  # RIGHT-TO-LEFT MARK
        "\u061c": None,  # ARABIC LETTER MARK
        "\u202a": None,  # LEFT-TO-RIGHT EMBEDDING
        "\u202b": None,  # RIGHT-TO-LEFT EMBEDDING
        "\u202c": None,  # POP DIRECTIONAL FORMATTING
        "\u202d": None,  # LEFT-TO-RIGHT OVERRIDE
        "\u202e": None,  # RIGHT-TO-LEFT OVERRIDE
        "\u2066": None,  # LEFT-TO-RIGHT ISOLATE
        "\u2067": None,  # RIGHT-TO-LEFT ISOLATE
        "\u2068": None,  # FIRST STRONG ISOLATE
        "\u2069": None,  # POP DIRECTIONAL ISOLATE
        "\u2010": "-",  # HYPHEN
        "\u2011": "-",  # NON-BREAKING HYPHEN
        "\u2012": "-",  # FIGURE DASH
        "\u2013": "-",  # EN DASH
        "\u2014": "-",  # EM DASH
        "\u2015": "-",  # HORIZONTAL BAR
        "\u2009": " ",  # THIN SPACE
        "\u200a": " ",  # HAIR SPACE
        "\u202f": " ",  # NARROW NO-BREAK SPACE
    }
)

# A zero-width space or word joiner between two digits is a boundary, not glue:
# deleting it would merge "5\u200b6" into 56.
_JOINER_BETWEEN_DIGITS = re.compile(r"(?<=\d)[\u200b\u2060]+(?=\d)")


def _class_names(tokens: list[Token]) -> str:
    """
    Semiotic class names in ``tokens``, for logging a failure without its values.
    """
    names: list[str] = []
    for token in tokens:
        # Tagged tokens nest as ``tokens { <class> { ... } }``, so the class is one level in.
        for key, value in token.items():
            names.extend(value if isinstance(value, dict) else [key])
    return ", ".join(names) or "none"


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

    def normalize(self, text: str) -> str:
        """
        Transduce ``text`` through the tagger and verbalizer.

        Returns the input unchanged when it is empty or cannot be transduced.
        """
        text = unicodedata.normalize("NFC", text)
        text = _JOINER_BETWEEN_DIGITS.sub(" ", text).translate(_PRE_CLEAN)
        text = _SPACE_DUP.sub(" ", text.strip())
        if not text:
            return text
        escaped = pynini.escape(text)
        try:
            tagged_lattice = escaped @ self.classify
            tagged_text = pynini.shortestpath(tagged_lattice, nshortest=1, unique=True).string()
        except Exception as exc:
            # Warnings stay content-free; callers normalize phone numbers and money.
            logger.warning("Failed to tag text (%d chars): %s", len(text), type(exc).__name__)
            logger.debug("Failed to tag text: %s", text)
            return text

        try:
            # Per-call: TokenParser holds mutable cursor state, so sharing it is not thread-safe.
            parser = TokenParser()
            parser(tagged_text)
            tokens = parser.parse()
            output = self._verbalize(tokens, tagged_text)
        except Exception as exc:
            logger.warning("Failed to verbalize text (%d chars): %s", len(text), type(exc).__name__)
            logger.debug("Failed to verbalize text: %s", text)
            return text
        if output is None:
            return text
        return _SPACE_DUP.sub(" ", output).strip()

    def _verbalize(self, tokens: list[Token], tagged_text: str) -> str | None:
        """
        Verbalize the token list, choosing each token's field order independently.

        Field orders are resolved one token at a time (the verbalizer accepts tokens
        independently), so the search is linear in the number of tokens rather than a
        cartesian product over all of them.
        """
        chosen: list[str] = []
        for token in tokens:
            for candidate in self._permute(token):
                lattice = pynini.escape(candidate) @ self.verbalize
                if lattice.num_states() != 0:
                    chosen.append(candidate)
                    break
            else:
                logger.warning("No verbalization found for class: %s", _class_names([token]))
                logger.debug("No verbalization found for: %s", tagged_text)
                return None
        lattice = pynini.escape("".join(chosen)) @ self.verbalize
        if lattice.num_states() == 0:
            logger.warning("No verbalization found for classes: %s", _class_names(tokens))
            logger.debug("No verbalization found for: %s", tagged_text)
            return None
        path: str = pynini.shortestpath(lattice, nshortest=1, unique=True).string()
        return path

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
