"""
TN tagger for money amounts, shared by every language.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst, insert_space
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.tn_taggers.quantities import quantity_words
from indic_text_normalization.core.utils import data_path, load_labels

# Single-character currency symbols; only these own a bare ".50" minor amount.
SYMBOLS = ("₹", "$", "£", "€", "¥", "₩")


class MoneyFst(GraphFst):
    """
    Finite state transducer for classifying money, e.g.
        ₹50 -> money { currency_maj: "రూపాయి" integer_part: "యాభై" }
        ₹50.50 -> money { currency_maj: "రూపాయి" integer_part: "యాభై" fractional_part: "యాభై" currency_min: "centiles" }
        ₹5 కోట్లు -> money { currency_maj: "రూపాయి" integer_part: "ఐదు కోట్లు" }
        ₹150కి -> money { currency_maj: "రూపాయి" integer_part: "నూట యాభై" suffix: "కి" }

    The ``centiles`` placeholder is resolved by the language's verbalizer to the minor
    currency word. Reads ``money/currency.tsv`` (symbol or code -> singular word) and
    ``numbers/quantity_words.tsv``.

    Attributes
    ----------
    cardinal : ``CardinalBase``
        The language's cardinal.
    amount_before_scale : ``pynini.Fst | None``, optional (default = None)
        Rewrite applied to a spoken amount that stands before a scale word (the Telugu
        oblique: ఐదు వందలు కోట్లు -> ఐదు వందల కోట్లు). None leaves the amount as spoken.
    inflected_quantity : ``pynini.Fst | None``, optional (default = None)
        A written scale word carrying a case ending that is not a plain glued suffix
        (Malayalam കോടിക്ക്), mapped to ``<scale word>" suffix: "<written suffix>`` so the
        verbalizer attaches the suffix to the currency word (അഞ്ച് കോടി രൂപയ്ക്ക്).
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: CardinalBase,
        *,
        amount_before_scale: pynini.Fst | None = None,
        inflected_quantity: pynini.Fst | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="money", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        native_digit = profile.digits.digit
        native_zero = profile.digits.zero
        currency_rows = load_labels(data_path(profile.lang, "money/currency.tsv"), min_fields=2)
        currency_graph = pynini.string_map([(k, v) for k, v, *_ in currency_rows]).optimize()
        rupee_word = dict((k, v) for k, v, *_ in currency_rows)["₹"]
        zero_word = pynini.project(cardinal.zero, "output").string()
        quantities = quantity_words(profile.lang)

        cardinal_graph = cardinal.final_graph

        optional_graph_negative = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("-", '"true"') + insert_space,
            0,
            1,
        )
        currency_major = pynutil.insert('currency_maj: "') + currency_graph + pynutil.insert('"')
        optional_space = pynini.closure(pynini.accep(" "), 0, 1)
        range_word, range_tail = profile.range_phrase
        range_amount = (
            cardinal_graph
            + pynini.cross("-", range_word)
            + cardinal_graph
            + pynutil.insert(range_tail)
        )
        # A range costs two more copies of the cardinal, so it gets one branch of its own
        # rather than riding inside every branch that takes an amount.
        integer = (
            pynutil.insert('integer_part: "')
            + pynutil.add_weight(cardinal_graph, -0.1)
            + pynutil.insert('"')
        )
        integer_range = (
            pynutil.insert('integer_part: "')
            + pynutil.add_weight(range_amount, -0.05)
            + pynutil.insert('"')
        )
        # ₹50.5 means 50 paise: a lone fractional digit is scaled by ten before lookup.
        one_digit_padded = pynini.union(
            DIGIT + pynutil.insert("0"), native_digit + pynutil.insert(native_zero)
        )
        # .05 is five paise: a leading zero in the minor unit is dropped.
        zero_lead = pynini.union(
            pynutil.delete("0") + DIGIT, pynutil.delete(native_zero) + native_digit
        )
        two_digits = pynini.union(
            pynini.difference(DIGIT, "0") + DIGIT,
            pynini.difference(native_digit, native_zero) + native_digit,
        )
        fraction_digits = pynini.union(one_digit_padded, zero_lead, two_digits).optimize()
        fraction = (
            pynutil.insert('fractional_part: "')
            + (fraction_digits @ cardinal_graph)
            + pynutil.insert('"')
        )
        currency_minor = pynutil.insert('currency_min: "centiles"')

        optional_slash_dash = pynini.closure(
            pynutil.add_weight(
                pynini.closure(pynini.accep(" "), 0, 1) + pynutil.delete("/-"), -0.1
            ),
            0,
            1,
        )

        graph_major_only = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer
            + optional_slash_dash
        )
        graph_major_and_minor = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer
            + optional_space
            + pynini.cross(".", " ")
            + fraction
            + insert_space
            + currency_minor
            + optional_slash_dash
        )

        graph_major_only_suffix = (
            optional_graph_negative
            + integer
            + insert_space
            + optional_space
            + currency_major
            + optional_slash_dash
        )
        graph_major_and_minor_suffix = (
            optional_graph_negative
            + integer
            + optional_space
            + pynini.cross(".", " ")
            + fraction
            + optional_space
            + insert_space
            + currency_minor
            + insert_space
            + currency_major
            + optional_slash_dash
        )

        # ₹5 కోట్లు style: the amount carries a scale word and the currency reads after it.
        # English scale words and the shorthands L/cr/K/M/B are spoken natively (₹2 lakh,
        # ₹15L, $50M); two scale words may stack (₹1 లక్ష కోట్లు).
        quantity_word = (
            pynini.accep(" ") + quantities.spaced
            | pynutil.delete(pynini.closure(" ", 0, 1)) + insert_space + quantities.short
        ) + pynini.closure(pynini.accep(" ") + quantities.native, 0, 1)
        single_frac_digit = profile.any_digit @ cardinal_graph
        point_word = f" {profile.point_word} "
        amount_with_point = cardinal_graph + pynini.closure(
            pynini.cross(".", point_word) + (cardinal.digit_by_digit | single_frac_digit),
            0,
            1,
        )
        # ₹5-10 కోట్లు reads as a range amount.
        amount_with_point |= (
            amount_with_point
            + pynini.cross("-", range_word)
            + amount_with_point
            + pynutil.insert(range_tail)
        )
        amount_scaled = amount_with_point
        if amount_before_scale is not None:
            amount_scaled = (amount_with_point @ amount_before_scale).optimize()
        graph_quantity = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + amount_scaled
            + quantity_word
            + pynutil.insert('"')
            + optional_slash_dash
        )

        # ₹50.123: three or more minor digits are not paise; read as a decimal amount.
        long_fraction = pynini.compose(
            pynini.closure(profile.any_digit, 3), cardinal.digit_by_digit
        )
        graph_long_fraction = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + pynutil.insert('integer_part: "')
            + cardinal_graph
            + pynini.cross(".", point_word)
            + long_fraction
            + pynutil.insert('"')
        )

        # 50/- with no symbol is rupees.
        graph_slash_rupee = (
            pynutil.insert(f'currency_maj: "{rupee_word}"')
            + insert_space
            + integer
            + optional_space
            + pynutil.delete("/-")
        )

        # A trailing .00 minor part is silent (₹1,999.00 -> ...రూపాయలు).
        delete_zero_frac = pynutil.delete(
            pynini.union(".00", "." + native_zero + native_zero, ".0", "." + native_zero)
        )
        graph_zero_frac = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer
            + delete_zero_frac
            + optional_slash_dash
        )

        # ₹.50 reads as paise only (symbol currencies only: Rs./రూ. own the dot).
        symbol_currency = pynini.compose(pynini.union(*SYMBOLS), currency_graph)
        currency_symbol_major = (
            pynutil.insert('currency_maj: "') + symbol_currency + pynutil.insert('"')
        )
        graph_bare_paise = (
            currency_symbol_major
            + optional_space
            + insert_space
            + pynutil.insert(f'integer_part: "{zero_word}"')
            + pynini.cross(".", " ")
            + fraction
            + insert_space
            + currency_minor
        )

        # ₹-500: the sign may follow the symbol.
        negative_after_currency = (
            currency_major
            + optional_space
            + pynutil.insert(" negative: ")
            + pynini.cross("-", '"true"')
            + optional_space
            + insert_space
            + integer
            + optional_slash_dash
        )

        graph_range = (
            optional_graph_negative
            + currency_major
            + optional_space
            + insert_space
            + integer_range
            + optional_slash_dash
        )

        graph_currencies = (
            graph_major_only
            | graph_range
            | graph_major_and_minor
            | pynutil.add_weight(graph_quantity, -0.2)
            | pynutil.add_weight(graph_long_fraction, 0.2)
            | pynutil.add_weight(graph_slash_rupee, -0.1)
            | pynutil.add_weight(graph_zero_frac, -0.1)
            | pynutil.add_weight(graph_bare_paise, -0.1)
            | pynutil.add_weight(negative_after_currency, 0.1)
            | pynutil.add_weight(graph_major_only_suffix | graph_major_and_minor_suffix, 0.5)
        )

        if profile.case_suffixes:
            # ₹150కి: a case suffix on the amount is carried as a field and attached to
            # the currency word by the verbalizer; it may also follow a scale word.
            case_suffix = (
                pynutil.insert(' suffix: "')
                + pynini.union(*profile.case_suffixes)
                + pynutil.insert('"')
            )
            graph_major_kku = (
                optional_graph_negative
                + currency_major
                + optional_space
                + insert_space
                + pynutil.insert('integer_part: "')
                + (amount_scaled + quantity_word | amount_with_point | cardinal_graph)
                + pynutil.insert('"')
                + case_suffix
            )
            # ₹50.50కి: a case suffix after a paise amount attaches to the minor
            # currency word, not to the major one.
            graph_minor_kku = (
                optional_graph_negative
                + currency_major
                + optional_space
                + insert_space
                + integer
                + optional_space
                + pynini.cross(".", " ")
                + fraction
                + insert_space
                + currency_minor
                + case_suffix
            )
            graph_currencies |= pynutil.add_weight(graph_major_kku, -0.1)
            graph_currencies |= pynutil.add_weight(graph_minor_kku, -0.2)
        if inflected_quantity is not None:
            graph_inflected = (
                optional_graph_negative
                + currency_major
                + optional_space
                + insert_space
                + pynutil.insert('integer_part: "')
                + amount_scaled
                + pynini.accep(" ")
                + inflected_quantity
                + pynutil.insert('"')
            )
            graph_currencies |= pynutil.add_weight(graph_inflected, -0.1)

        self.fst = self.add_tokens(graph_currencies.optimize())
