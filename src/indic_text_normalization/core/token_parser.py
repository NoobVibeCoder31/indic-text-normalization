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
Parser for the tagged-token string emitted by classify grammars.
"""

import string
from collections import OrderedDict

PRESERVE_ORDER_KEY = "preserve_order"
EOS = "<EOS>"

TokenValue = str | dict[str, "TokenValue"]
Token = dict[str, TokenValue]


class TokenParser:
    """
    Parse a tagged string such as ``tokens { money { integer: "20" currency: "$" } }``
    into a list of nested dictionaries.
    """

    def __call__(self, text: str) -> None:
        """
        Prepare the parser for the given non-empty tagged text.
        """
        self.text = text
        self.len_text = len(text)
        self.char = text[0]
        self.index = 0

    def parse(self) -> list[Token]:
        """
        Parse the prepared text into a list of token dictionaries.
        """
        tokens = []
        while self.parse_ws():
            token = self.parse_token()
            if not token:
                break
            tokens.append(token)
        return tokens

    def parse_token(self) -> Token | None:
        """
        Parse one ``key value`` pair into a single-entry dictionary.
        """
        d: Token = OrderedDict()
        key = self.parse_string_key()
        if key is None:
            return None
        self.parse_ws()
        value: TokenValue
        if key == PRESERVE_ORDER_KEY:
            self.parse_char(":")
            self.parse_ws()
            self.parse_chars("true")
            value = "true"
        else:
            value = self.parse_token_value()

        d[key] = value
        return d

    def parse_token_value(self) -> TokenValue:
        """
        Parse a quoted string value or a nested ``{ ... }`` dictionary.
        """
        if self.char == ":":
            self.parse_char(":")
            self.parse_ws()
            self.parse_char('"')
            value_string = self.parse_string_value()
            self.parse_char('"')
            return value_string
        if self.char == "{":
            d: dict[str, TokenValue] = OrderedDict()
            self.parse_char("{")
            for tok_dict in self.parse():
                for k, v in tok_dict.items():
                    d[k] = v
            self.parse_char("}")
            return d
        raise ValueError(f"Unexpected character {self.char!r} at index {self.index}.")

    def parse_char(self, exp: str) -> bool:
        """
        Consume one expected character.
        """
        if self.char != exp:
            raise ValueError(f"Expected {exp!r}, found {self.char!r} at index {self.index}.")
        self.read()
        return True

    def parse_chars(self, exp: str) -> bool:
        """
        Consume a sequence of expected characters.
        """
        ok = False
        for x in exp:
            ok |= self.parse_char(x)
        return ok

    def parse_string_key(self) -> str | None:
        """
        Parse a key of ASCII letters and underscores.
        """
        if self.char in string.whitespace or self.char == EOS:
            raise ValueError(f"Unexpected {self.char!r} at index {self.index}.")
        incl_criterium = string.ascii_letters + "_"
        chars = []
        while self.char in incl_criterium:
            chars.append(self.char)
            if not self.read():
                raise ValueError("Unexpected end of text while parsing a key.")

        if not chars:
            return None
        return "".join(chars)

    def parse_string_value(self) -> str:
        """
        Parse a quoted value; it ends at a quote followed by a space.
        """
        if self.char == EOS:
            raise ValueError("Unexpected end of text while parsing a value.")
        chars = []
        while self.char != '"' or self.text[self.index + 1] != " ":
            chars.append(self.char)
            if not self.read():
                raise ValueError("Unexpected end of text while parsing a value.")
        return "".join(chars)

    def parse_ws(self) -> bool:
        """
        Skip whitespace; return True unless the end of text was reached.
        """
        not_eos = self.char != EOS
        while not_eos and self.char == " ":
            not_eos = self.read()
        return not_eos

    def read(self) -> bool:
        """
        Advance to the next character; return True unless the end of text was reached.
        """
        if self.index < self.len_text - 1:
            self.index += 1
            self.char = self.text[self.index]
            return True
        self.char = EOS
        return False
