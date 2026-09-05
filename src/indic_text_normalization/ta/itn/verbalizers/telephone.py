"""
ITN verbalizer emitting written telephone numbers.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import NOT_QUOTE, GraphFst, delete_space, insert_space


class TelephoneFst(GraphFst):
    """
    Finite state transducer for verbalizing telephone numbers, e.g.
        telephone { number_part: "9943206870" } -> 9943206870
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="telephone", kind="verbalize", deterministic=deterministic)

        country_code = (
            pynutil.delete('country_code: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )
        number = (
            pynutil.delete('number_part: "') + pynini.closure(NOT_QUOTE, 1) + pynutil.delete('"')
        )

        self.graph = pynini.closure(country_code + delete_space + insert_space, 0, 1) + number
        self.fst = self.delete_tokens(self.graph).optimize()
