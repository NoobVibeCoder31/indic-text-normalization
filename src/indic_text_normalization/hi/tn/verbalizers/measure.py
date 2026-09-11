"""
Hindi TN measure verbalizer.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    NOT_QUOTE,
    GraphFst,
    delete_preserve_order,
    delete_space,
    insert_space,
)
from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.hi.constants import LANG, MINUS_WORD
from indic_text_normalization.hi.morphology import NBSP_TO_SPACE, NOT_ONE, ONE


class MeasureFst(GraphFst):
    """
    Finite state transducer for verbalizing measures, e.g.
        measure { amount: "पाँच" units: "किलोग्राम" } -> पाँच किलोग्राम
        measure { amount: "एक" units: "घंटा" } -> एक घंटा
        measure { amount: "पाँच" units: "घंटा" } -> पाँच घंटे

    The tagger carries the singular unit; a count other than one takes the plural column
    of the unit table (घंटा -> घंटे, महीना -> महीने; most units are invariant).
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="measure", kind="verbalize", deterministic=deterministic)

        optional_sign = pynini.closure(
            pynini.cross('negative: "true"', f"{MINUS_WORD} ") + delete_space, 0, 1
        )
        rows = [r for r in load_labels(data_path(LANG, "measure/unit.tsv")) if len(r) >= 3]
        nbsp = " "  # U+00A0 NO-BREAK SPACE, as the unit table values travel
        plural_pairs = {(sg.replace(" ", nbsp), pl.replace(" ", nbsp)) for _, sg, pl in rows}
        pluralize = pynini.string_map(sorted(plural_pairs)).optimize()
        singular = pynini.closure(NOT_QUOTE, 1)

        amount_one = pynutil.delete('amount: "') + pynini.accep(ONE) + pynutil.delete('"')
        amount_many = pynutil.delete('amount: "') + NOT_ONE + pynutil.delete('"')
        units_singular = pynutil.delete('units: "') + singular + pynutil.delete('"')
        units_plural = pynutil.delete('units: "') + (singular @ pluralize) + pynutil.delete('"')

        graph = optional_sign + (
            amount_one + delete_space + insert_space + units_singular
            | amount_many + delete_space + insert_space + units_plural
        )
        graph = (graph + delete_preserve_order) @ NBSP_TO_SPACE
        self.fst = self.delete_tokens(graph).optimize()
