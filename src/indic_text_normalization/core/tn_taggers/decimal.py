"""
TN tagger for decimals, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst, insert_space
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase, delete_commas
from indic_text_normalization.core.tn_taggers.quantities import quantity_words


class DecimalFst(GraphFst):
    """
    Finite state transducer for classifying decimals, e.g.
        -12.5006 కోట్లు -> decimal { negative: "true" integer_part: "పన్నెండు" fractional_part: "ఐదు సున్నా సున్నా ఆరు" quantity: "కోట్లు" }
        1 కోటి -> decimal { integer_part: "ఒకటి" quantity: "కోటి" }
        .5 -> decimal { integer_part: "సున్నా" fractional_part: "ఐదు" }
        1.2.3 -> decimal { integer_part: "ఒకటి" fractional_part: "రెండు దశాంశం మూడు" }

    Attributes
    ----------
    graph : ``pynini.Fst``
        Digits in either script read one at a time (the fractional reading).
    """

    def __init__(self, cardinal: CardinalBase, deterministic: bool = True) -> None:
        super().__init__(name="decimal", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        graph_digit = cardinal.digit | cardinal.zero
        cardinal_graph = cardinal.final_graph

        native_sequence = (graph_digit + pynini.closure(insert_space + graph_digit)).optimize()
        ascii_sequence = pynini.compose(
            pynini.closure(DIGIT, 1), profile.to_native @ native_sequence
        ).optimize()
        self.graph = (native_sequence | ascii_sequence).optimize()

        point = pynutil.delete(".")

        optional_graph_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true"') + insert_space,
            0,
            1,
        )

        integer_with_commas = pynini.compose(
            delete_commas(profile.any_digit), cardinal_graph
        ).optimize()
        integer_graph = pynutil.add_weight(integer_with_commas, -0.1) | cardinal_graph

        self.graph_fractional = (
            pynutil.insert('fractional_part: "')
            + (self.graph | pynutil.add_weight(cardinal.attach_case_suffix(self.graph), 0.1))
            + pynutil.insert('"')
        )
        self.graph_integer = pynutil.insert('integer_part: "') + integer_graph + pynutil.insert('"')

        final_graph_wo_sign = self.graph_integer + point + insert_space + self.graph_fractional

        # Bare-dot decimals: .5 reads as <zero> <point> <five>.
        zero_word = pynini.project(cardinal.zero, "output").string()
        bare_dot = (
            pynutil.insert(f'integer_part: "{zero_word}"')
            + point
            + insert_space
            + self.graph_fractional
        )
        # Dotted chains (versions, IPs): every segment after the first reads
        # digit-by-digit with the point word between them.
        dotted_chain = (
            self.graph_integer
            + point
            + insert_space
            + pynutil.insert('fractional_part: "')
            + self.graph
            + pynini.closure(pynini.cross(".", f" {profile.point_word} ") + self.graph, 1)
            + pynutil.insert('"')
        )
        final_graph_wo_sign |= pynutil.add_weight(bare_dot, 0.1)
        final_graph_wo_sign |= pynutil.add_weight(dotted_chain, 0.5)

        # A cardinal or decimal followed by a quantity word (5 లక్షలు, 1.5 కోట్లు, 2 lakh).
        quantity = (
            pynutil.delete(" ")
            + insert_space
            + pynutil.insert('quantity: "')
            + quantity_words(profile.lang).spaced
            + pynutil.insert('"')
        )
        with_quantity = (
            pynutil.insert('integer_part: "') + integer_graph + pynutil.insert('"') + quantity
        )
        with_quantity |= final_graph_wo_sign + quantity

        self.final_graph_wo_negative = final_graph_wo_sign | with_quantity
        final_graph = optional_graph_negative + self.final_graph_wo_negative
        self.fst = self.add_tokens(final_graph).optimize()
