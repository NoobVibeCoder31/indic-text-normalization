"""
TN tagger for measures (a number with a unit), shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import (
    TO_LOWER,
    GraphFst,
    convert_space,
    delete_zero_or_one_space,
)
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.tn_taggers.decimal import DecimalFst
from indic_text_normalization.core.utils import data_path, load_labels

# Single letters that are far more often part of an identifier (47A, 5G) than a unit.
ID_PRONE = frozenset("ABCGJKNVWXbdhqsx*")


class MeasureFst(GraphFst):
    """
    Finite state transducer for classifying measures, e.g.
        5 కి.మీ. -> measure { amount: "ఐదు" units: "కిలోమీటర్" preserve_order: true }
        12.5kg -> measure { amount: "పన్నెండు దశాంశం ఐదు" units: "కిలోగ్రామ్" preserve_order: true }
        5 kgలో -> measure { amount: "ఐదు" units: "కిలోగ్రామ్" suffix: "లో" preserve_order: true }

    The unit travels in its singular form (column 2 of ``measure/unit.tsv``); the
    language's verbalizer picks singular or plural.
    """

    def __init__(
        self, cardinal: CardinalBase, decimal: DecimalFst, deterministic: bool = True
    ) -> None:
        super().__init__(name="measure", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        rows = [r for r in load_labels(data_path(profile.lang, "measure/unit.tsv")) if len(r) >= 2]
        multi = pynini.string_map(
            [(k, v) for k, v, *_ in rows if len(k) > 1 or k not in ID_PRONE]
        ).optimize()
        single = pynini.string_map([(k, v) for k, v, *_ in rows if len(k) == 1]).optimize()

        # Accept uppercase spellings of Latin units (5KG).
        lowercase = pynini.closure(TO_LOWER | pynini.union(*"abcdefghijklmnopqrstuvwxyz°²./"), 2)
        multi |= pynini.compose(lowercase, multi).optimize()

        unit_multi = convert_space(multi).optimize()
        unit_single = convert_space(single).optimize()

        amount = pynini.union(
            cardinal.final_graph,
            cardinal.final_graph + pynini.cross(".", f" {profile.point_word} ") + decimal.graph,
        ).optimize()
        # 5-10 kg reads as a range amount.
        between, after = profile.range_phrase
        amount = pynini.union(
            amount, amount + pynini.cross("-", between) + amount + pynutil.insert(after)
        ).optimize()

        optional_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true" '), 0, 1
        )

        unit_part = (delete_zero_or_one_space + unit_multi) | (pynutil.delete(" ") + unit_single)

        suffix = (
            pynini.closure(
                pynutil.insert(' suffix: "')
                + pynini.union(*profile.case_suffixes)
                + pynutil.insert('"'),
                0,
                1,
            )
            if profile.case_suffixes
            else pynini.accep("")
        )

        graph = (
            optional_negative
            + pynutil.insert('amount: "')
            + amount
            + pynutil.insert('"')
            + pynutil.insert(' units: "')
            + unit_part
            + pynutil.insert('"')
            + suffix
            + pynutil.insert(" preserve_order: true")
        )
        self.fst = self.add_tokens(graph).optimize()
