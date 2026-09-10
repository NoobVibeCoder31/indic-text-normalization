"""
ITN tagger converting spoken Tamil money amounts to symbol-and-digit form.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.core.graph_utils import delete_space, DIGIT, GraphFst
from indic_text_normalization.ta.constants import LANG
from indic_text_normalization.ta.itn.fused import half_form_rows, quarter_form_graph
from indic_text_normalization.core.scales import kept_scale_words
from indic_text_normalization.ta.itn.taggers.cardinal import CardinalFst


class MoneyFst(GraphFst):
    """
    Finite state transducer for classifying spoken money, e.g.
        ஐம்பது ரூபாய் -> money { currency: "₹" integer_part: "50" }
        ஐம்பது ரூபாய் ஐம்பது பைசா -> money { currency: "₹" integer_part: "50" fractional_part: "50" }
    """

    def __init__(self, cardinal: CardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="money", kind="classify", deterministic=deterministic)

        major_rows = load_labels(data_path(LANG, "money/currency_itn.tsv"), min_fields=2)
        # Every minor unit TN can emit inverts to its major currency's symbol, derived from
        # the same table TN verbalizes from so the two directions cannot drift apart. The
        # extras table adds only what that pairing cannot give: plurals and ₹ காசு.
        major_to_symbol = dict(major_rows)
        minor_rows = [
            [minor, major_to_symbol[major]]
            for major, minor in load_labels(
                data_path(LANG, "money/major_minor_currencies.tsv"), min_fields=2
            )
            if major in major_to_symbol
        ]
        minor_rows += [
            row
            for row in load_labels(data_path(LANG, "money/minor_unit_itn.tsv"), min_fields=2)
            if tuple(row) not in {tuple(r) for r in minor_rows}
        ]
        currency = pynini.string_map(major_rows)
        minor = pynini.string_map(minor_rows)
        # A minor unit belongs to one major currency: பைசா is rupees, சென்ட் is dollars.
        # Grouping them by symbol keeps ஐந்து டாலர் ஐம்பது பைசா from reading as $5.50.
        majors_by_symbol: dict[str, list[str]] = {}
        minors_by_symbol: dict[str, list[str]] = {}
        for word, symbol in major_rows:
            majors_by_symbol.setdefault(symbol, []).append(word)
        for word, symbol in minor_rows:
            minors_by_symbol.setdefault(symbol, []).append(word)

        number = cardinal.words_to_digits_with_article
        # Only one or two minor-unit digits are paise; more digits are not an amount.
        minor_digits = number @ pynini.closure(DIGIT, 1, 2)

        integer_part = pynutil.insert('integer_part: "') + number + pynutil.insert('"')
        fractional_part = pynutil.insert(' fractional_part: "') + minor_digits + pynutil.insert('"')

        graph = (
            integer_part
            + delete_space
            + pynutil.insert(' currency: "')
            + currency
            + pynutil.insert('"')
        )
        for symbol, minor_words in minors_by_symbol.items():
            if symbol not in majors_by_symbol:
                continue
            graph |= (
                integer_part
                + delete_space
                + pynutil.insert(f' currency: "{symbol}"')
                + pynutil.delete(pynini.union(*majors_by_symbol[symbol]))
                + delete_space
                + fractional_part
                + delete_space
                + pynutil.delete(pynini.union(*minor_words))
            )

        # Currency word first: ரூபாய் ஐம்பது -> ₹50.
        currency_first = (
            pynutil.insert('currency: "')
            + currency
            + pynutil.insert('"')
            + delete_space
            + pynutil.insert(" ")
            + integer_part
            + pynutil.insert(" preserve_order: true")
        )
        graph |= currency_first

        # Quantity-word money keeps the written idiom: ஐந்து கோடி ரூபாய் -> ₹5 கோடி,
        # இரண்டு புள்ளி ஐந்து லட்சம் ரூபாய் -> ₹2.5 லட்சம். The amount before the scale word
        # is at most three digits, so a fully spoken number (ஐந்து கோடி ஐம்பது லட்சம்) is
        # read as one cardinal instead.
        short = (number @ pynini.closure(DIGIT, 1, 3)).optimize()
        amount_digits = pynini.union(
            short,
            short + pynini.cross(" புள்ளி ", ".") + short,
            pynini.union(*[pynini.cross(word, f"{ip}.{fp}") for word, ip, fp in half_form_rows()]),
            quarter_form_graph(short, prefix="", infix=".", suffix=lambda fraction: fraction),
        )
        quantity_amount = (
            pynutil.insert('integer_part: "')
            + amount_digits
            + pynini.accep(" ")
            + pynini.union(*kept_scale_words(LANG))
            + pynutil.insert('"')
        )
        graph_quantity = (
            quantity_amount
            + delete_space
            + pynutil.insert(' currency: "')
            + currency
            + pynutil.insert('"')
        )
        graph |= pynutil.add_weight(graph_quantity, -1.0)

        # Minor-unit-only amounts: ஐம்பது பைசா -> ₹0.50, ஐம்பது சென்ட் -> $0.50.
        minor_only = (
            pynutil.insert('fractional_part: "')
            + minor_digits
            + pynutil.insert('"')
            + delete_space
            + pynutil.insert(' currency: "')
            + minor
            + pynutil.insert('" integer_part: "0"')
        )
        graph |= minor_only

        # Spoken minus folds into the amount: மைனஸ் ஐந்நூறு ரூபாய் -> -₹500.
        optional_minus = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("மைனஸ் ", '"true" '), 0, 1
        )
        self.fst = self.add_tokens(optional_minus + graph).optimize()
