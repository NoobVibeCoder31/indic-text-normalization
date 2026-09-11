"""
Hindi TN money verbalizer.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SPACE, GraphFst
from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.hi.constants import LANG, MINUS_WORD
from indic_text_normalization.hi.morphology import NOT_ONE, ONE


class MoneyFst(GraphFst):
    """
    Finite state transducer for verbalizing money, e.g.
        money { integer_part: "पचास" currency_maj: "रुपया" } -> पचास रुपये
        money { integer_part: "एक" currency_maj: "रुपया" } -> एक रुपया
        money { integer_part: "पचास" currency_maj: "रुपया" fractional_part: "पचास" currency_min: "centiles" } -> पचास रुपये पचास पैसे
        money { currency_maj: "रुपया" integer_part: "शून्य" fractional_part: "एक" currency_min: "centiles" } -> एक पैसा

    रुपया and पैसा take their plural after any count but one; the other currencies are invariant.
    """

    def __init__(self, deterministic: bool = True) -> None:
        super().__init__(name="money", kind="verbalize", deterministic=deterministic)

        forms = {
            sg: pl
            for sg, pl, *_ in load_labels(data_path(LANG, "money/currency_forms.tsv"), min_fields=2)
        }
        major_minor = dict(
            (row[0], row[1])
            for row in load_labels(
                data_path(LANG, "money/major_minor_currencies.tsv"), min_fields=2
            )
        )
        integer_one = pynutil.delete('integer_part: "') + pynini.accep(ONE) + pynutil.delete('"')
        integer_many = pynutil.delete('integer_part: "') + NOT_ONE + pynutil.delete('"')
        zero_integer = pynutil.delete('integer_part: "शून्य"')
        minor_field = pynutil.delete('currency_min: "centiles"')

        graphs = []
        for major, minor in major_minor.items():
            if major not in forms:
                continue
            currency = (
                pynutil.delete('currency_maj: "') + pynutil.delete(major) + pynutil.delete('"')
            )
            fraction = (
                pynutil.delete('fractional_part: "')
                + pynini.accep(ONE)
                + pynutil.delete('"')
                + SPACE
                + minor_field
                + pynutil.insert(minor)
            ) | (
                pynutil.delete('fractional_part: "')
                + NOT_ONE
                + pynutil.delete('"')
                + SPACE
                + minor_field
                + pynutil.insert(forms[minor])
            )
            graphs.append(integer_one + SPACE + currency + pynutil.insert(major))
            graphs.append(integer_many + SPACE + currency + pynutil.insert(forms[major]))
            graphs.append(integer_one + SPACE + currency + pynutil.insert(major) + SPACE + fraction)
            graphs.append(
                integer_many + SPACE + currency + pynutil.insert(forms[major]) + SPACE + fraction
            )
            graphs.append(
                pynutil.add_weight(
                    zero_integer
                    + pynutil.delete(SPACE)
                    + currency
                    + pynutil.delete(SPACE)
                    + fraction,
                    -0.1,
                )
            )
        optional_sign = pynini.closure(pynini.cross('negative: "true" ', f"{MINUS_WORD} "), 0, 1)
        self.fst = self.delete_tokens(optional_sign + pynini.union(*graphs)).optimize()
