"""
ITN tagger converting spoken money amounts to symbol-and-digit form, shared by every language.
"""

from collections.abc import Callable, Iterable

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst, delete_space
from indic_text_normalization.core.itn_taggers.cardinal import ItnCardinalFst, optional_sign_field
from indic_text_normalization.core.scales import kept_scale_words
from indic_text_normalization.core.utils import data_path, load_labels

Inflect = Callable[[str, str], str]


def inflection_maps(
    lang: str, written_suffixes: Iterable[str], inflect: Inflect
) -> tuple[pynini.Fst, dict[str, pynini.Fst], pynini.Fst]:
    """
    Build the three inflected-word maps ``ItnMoneyFst`` takes for a language whose case
    suffix changes shape on the noun (Malayalam രൂപയ്ക്ക്, Kannada ರೂಪಾಯಿಗೆ).

    Parameters
    ----------
    lang : ``str``
        Language whose money tables are read.
    written_suffixes : ``Iterable[str]``
        The written suffixes ITN emits after a digit (ന്, ൽ; ಕ್ಕೆ, ರಲ್ಲಿ).
    inflect : ``Callable[[str, str], str]``
        The spoken form of a noun carrying a written suffix (രൂപ, ന് -> രൂപയ്ക്ക്).

    Returns
    -------
    ``tuple[pynini.Fst, dict[str, pynini.Fst], pynini.Fst]``
        ``inflected_currency``, ``inflected_minor`` by symbol, and ``scaled_currency``.
    """
    suffixes = list(dict.fromkeys(written_suffixes))
    currency_rows = load_labels(data_path(lang, "money/currency_itn.tsv"), min_fields=2)
    currency = pynini.string_map(
        [
            (inflect(word, written), f' currency: "{symbol}" suffix: "{written}"')
            for word, symbol in currency_rows
            for written in suffixes
        ]
    ).optimize()

    symbol_of = dict(currency_rows)
    forms = {
        row[0]: row
        for row in load_labels(data_path(lang, "money/currency_forms.tsv"), min_fields=1)
    }
    by_symbol: dict[str, list[tuple[str, str]]] = {}
    for major, minor in load_labels(
        data_path(lang, "money/major_minor_currencies.tsv"), min_fields=2
    ):
        if major not in symbol_of:
            continue
        for word in dict.fromkeys(forms.get(minor, [minor])):
            for written in suffixes:
                by_symbol.setdefault(symbol_of[major], []).append(
                    (inflect(word, written), f' suffix: "{written}"')
                )
    minor_maps = {sym: pynini.string_map(pairs).optimize() for sym, pairs in by_symbol.items()}

    scaled = pynini.string_map(
        [
            (f"{scale} {inflect(word, written)}", f'{inflect(scale, written)}" currency: "{symbol}')
            for scale in kept_scale_words(lang)
            for word, symbol in currency_rows
            for written in suffixes
        ]
    ).optimize()
    return currency, minor_maps, scaled


def _minor_unit_rows(lang: str, major_to_symbol: dict[str, str]) -> list[list[str]]:
    """
    Every minor-unit word TN can emit, paired with its major currency's symbol.

    The rows are derived from the same tables the TN money verbalizer reads, so the two
    directions cannot drift apart; the extras table adds only what that pairing cannot
    give (an English plural TN never emits).
    """
    forms = {
        row[0]: row
        for row in load_labels(data_path(lang, "money/currency_forms.tsv"), min_fields=1)
    }
    rows = [
        [word, major_to_symbol[major]]
        for major, minor in load_labels(
            data_path(lang, "money/major_minor_currencies.tsv"), min_fields=2
        )
        if major in major_to_symbol
        for word in forms.get(minor, [minor])
    ]
    seen = {tuple(row) for row in rows}
    rows += [
        row
        for row in load_labels(data_path(lang, "money/minor_unit_itn.tsv"), min_fields=2)
        if tuple(row) not in seen
    ]
    return rows


class ItnMoneyFst(GraphFst):
    """
    Finite state transducer for classifying spoken money, e.g.
        యాభై రూపాయలు -> money { integer_part: "50" currency: "₹" }
        యాభై రూపాయల యాభై పైసలు -> money { integer_part: "50" currency: "₹" fractional_part: "50" }
        ఐదు కోట్ల రూపాయలు -> money { integer_part: "5 కోట్లు" currency: "₹" }

    Attributes
    ----------
    cardinal : ``ItnCardinalFst``
        The language's ITN cardinal.
    quantity_nominative : ``dict[str, str]``
        Kept scale words in the form TN speaks before a currency word, mapped to the form
        the written idiom keeps (కోట్ల -> కోట్లు). Words not listed are kept as spoken.
    bare_scale_words : ``tuple[str, ...]``
        Scale words that alone count one (లక్ష రూపాయలు -> ₹1 లక్ష).
    inflected_currency : ``pynini.Fst | None``, optional (default = None)
        For a language whose case suffix changes shape on the currency word: the spoken
        inflected word to the tagged fields it stands for (രൂപയ്ക്ക് ->
        `` currency: "₹" suffix: "ന്"``). A plain glued suffix needs no such map.
    inflected_minor : ``dict[str, pynini.Fst] | None``, optional (default = None)
        Likewise for the minor-unit word, per currency symbol (പൈസയ്ക്ക് -> `` suffix: "ന്"``).
    scaled_currency : ``pynini.Fst | None``, optional (default = None)
        A kept scale word followed by an inflected currency word, to the scale word with
        the suffix glued to it and the currency field (കോടി രൂപയ്ക്ക് ->
        ``കോടിക്ക്" currency: "₹``), for ₹5 കോടിക്ക്.
    range_lower : ``pynini.Fst | None``, optional (default = None)
        For a language whose range word is glued to the lower bound (Kannada ಐದರಿಂದ ಹತ್ತು):
        the spoken lower bound with its range ending, to its digits.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    """

    def __init__(
        self,
        cardinal: ItnCardinalFst,
        *,
        quantity_nominative: dict[str, str],
        bare_scale_words: tuple[str, ...],
        inflected_currency: pynini.Fst | None = None,
        inflected_minor: dict[str, pynini.Fst] | None = None,
        scaled_currency: pynini.Fst | None = None,
        range_lower: pynini.Fst | None = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="money", kind="classify", deterministic=deterministic)

        profile = cardinal.profile
        lang = profile.lang
        major_rows = load_labels(data_path(lang, "money/currency_itn.tsv"), min_fields=2)
        minor_rows = _minor_unit_rows(lang, dict(major_rows))
        currency = pynini.string_map(major_rows)
        minor = pynini.string_map(minor_rows)
        # A minor unit belongs to one major currency: పైసా is rupees, సెంట్ is dollars.
        # Grouping them by symbol keeps ఐదు డాలర్లు యాభై పైసలు from reading as $5.50.
        majors_by_symbol: dict[str, list[str]] = {}
        minors_by_symbol: dict[str, list[str]] = {}
        for word, symbol in major_rows:
            majors_by_symbol.setdefault(symbol, []).append(word)
        for word, symbol in minor_rows:
            minors_by_symbol.setdefault(symbol, []).append(word)

        # A case suffix on the currency or minor-unit word is carried into the written
        # form (₹50కి, ₹50.50కి).
        optional_suffix = pynini.accep("")
        if profile.case_suffixes:
            optional_suffix = pynini.closure(
                pynutil.insert(' suffix: "')
                + pynini.union(*profile.case_suffixes)
                + pynutil.insert('"'),
                0,
                1,
            )
        currency_field = (
            pynutil.insert(' currency: "') + currency + pynutil.insert('"') + optional_suffix
        )

        amount_words = cardinal.words_to_digits
        if profile.counting_one:
            amount_words = pynini.union(amount_words, pynini.cross(profile.counting_one, "1"))
        range_words = (
            cardinal.words_to_digits
            + pynini.cross(" " + pynini.union(*profile.range_words) + " ", "-")
            + cardinal.words_to_digits
        )
        if profile.range_suffix:
            range_words += pynutil.delete(" " + profile.range_suffix)
        if range_lower is not None:
            range_words |= range_lower + pynini.cross(" ", "-") + cardinal.words_to_digits
        integer_part = (
            pynutil.insert('integer_part: "')
            + (amount_words | pynutil.add_weight(range_words, -0.5))
            + pynutil.insert('"')
        )
        # A lone fractional digit is a tens value in paise (ఐదు పైసలు -> .05).
        two_digits = pynini.union(DIGIT + DIGIT, pynutil.insert("0") + DIGIT)
        fractional_part = (
            pynutil.insert(' fractional_part: "')
            + (amount_words @ two_digits)
            + pynutil.insert('"')
        )

        graph = integer_part + delete_space + currency_field
        if inflected_currency is not None:
            graph |= integer_part + delete_space + inflected_currency
        for symbol, minor_words in minors_by_symbol.items():
            if symbol not in majors_by_symbol:
                continue
            minor_tail = pynutil.delete(pynini.union(*minor_words)) + optional_suffix
            if inflected_minor and symbol in inflected_minor:
                minor_tail |= inflected_minor[symbol]
            graph |= (
                integer_part
                + delete_space
                + pynutil.insert(f' currency: "{symbol}"')
                + pynutil.delete(pynini.union(*majors_by_symbol[symbol]))
                + delete_space
                + fractional_part
                + delete_space
                + minor_tail
            )

        # Currency word first: రూపాయలు యాభై -> ₹50.
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

        # Quantity-word money keeps the written idiom: ఐదు కోట్ల రూపాయలు -> ₹5 కోట్లు,
        # రెండు దశాంశం ఐదు లక్షల రూపాయలు -> ₹2.5 లక్షలు. Expanded scale words are digits.
        kept = kept_scale_words(lang)
        quantity_written = pynini.union(
            *[
                (
                    pynini.cross(word, quantity_nominative[word])
                    if word in quantity_nominative
                    else pynini.accep(word)
                )
                for word in kept
            ]
        )
        # Two scale words stack in the written idiom too: ఒక లక్ష కోట్ల రూపాయలు -> ₹1 లక్ష కోట్లు.
        stacked = pynini.union(*kept) + " " + quantity_written
        quantity_written = pynini.union(quantity_written, pynutil.add_weight(stacked, -0.1))
        short = cardinal.words_to_digits @ pynini.closure(DIGIT, 1, 2)
        frac_digits = short + pynini.closure(delete_space + short)
        point = pynini.cross(pynini.accep(" ") + pynini.union(*profile.point_words) + " ", ".")
        amount_digits = amount_words + pynini.closure(point + frac_digits, 0, 1)
        quantity_amount = (
            pynutil.insert('integer_part: "')
            + amount_digits
            + pynini.accep(" ")
            + quantity_written
            + pynutil.insert('"')
        )
        if bare_scale_words:
            # A bare scale word counts one: లక్ష రూపాయలు -> ₹1 లక్ష.
            quantity_amount |= (
                pynutil.insert('integer_part: "1 ')
                + pynini.union(*bare_scale_words)
                + pynutil.insert('"')
            )
        graph_quantity = quantity_amount + delete_space + currency_field
        if scaled_currency is not None:
            graph_quantity |= (
                pynutil.insert('integer_part: "')
                + amount_digits
                + pynini.accep(" ")
                + scaled_currency
                + pynutil.insert('"')
            )
        graph |= pynutil.add_weight(graph_quantity, -1.0)

        # Minor-unit-only amounts: యాభై పైసలు -> ₹0.50, యాభై సెంట్లు -> $0.50.
        minor_only = (
            pynutil.insert('integer_part: "0"')
            + fractional_part
            + delete_space
            + pynutil.insert(' currency: "')
            + minor
            + pynutil.insert('"')
            + optional_suffix
        )
        graph |= minor_only

        # A spoken sign folds into the amount: ఋణ ఐదు వందల రూపాయలు -> -₹500.
        self.fst = self.add_tokens(optional_sign_field(profile) + graph).optimize()
