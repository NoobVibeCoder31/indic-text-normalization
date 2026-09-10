"""
ITN tagger converting spoken numbers to ASCII digits, shared by every language.

The language contributes its TN cardinal (inverted here), a pre-map normalizing spoken
variants to the forms TN emits, and any readings beyond the TN grammar's range.
"""

from pathlib import Path

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, GraphFst, sequential, unweighted
from indic_text_normalization.core.profile import LanguageProfile
from indic_text_normalization.core.scales import expanded_scale_words
from indic_text_normalization.core.tn_taggers.cardinal_base import CardinalBase
from indic_text_normalization.core.utils import data_path, load_labels


def optional_sign_field(profile: LanguageProfile) -> pynini.Fst:
    """
    Consume a leading spoken sign word, emitting the ``negative``/``positive`` field.
    """
    negative = pynini.union(*[pynini.cross(w + " ", '"true" ') for w in profile.negative_words])
    positive = pynini.union(*[pynini.cross(w + " ", '"true" ') for w in profile.positive_words])
    return pynini.closure(
        pynutil.insert("negative: ") + negative | pynutil.insert("positive: ") + positive, 0, 1
    )


def half_form_rows(lang: str) -> list[list[str]]:
    """
    Rows of ``numbers/itn_half_forms.tsv`` (fused word, integer digits, fraction digits),
    or none when the language has no such table.
    """
    path = data_path(lang, "numbers/itn_half_forms.tsv")
    if not Path(path).exists():
        return []
    return load_labels(path, min_fields=3)


def _scale_expanded(profile: LanguageProfile, plain: pynini.Fst) -> pynini.Fst:
    """
    Multiply out a scale word small enough for it, e.g. ఐదు దశాంశం ఐదు వేలు -> 5500.
    """
    words_by_zeros: dict[int, list[str]] = {}
    for word, zeros in expanded_scale_words(profile.lang):
        words_by_zeros.setdefault(zeros, []).append(word)
    if not words_by_zeros:
        return pynini.Fst()

    half_rows = half_form_rows(profile.lang)
    point = pynutil.delete(" " + pynini.union(*profile.point_words) + " ")
    graphs = []
    for zeros, words in words_by_zeros.items():
        tail = pynutil.delete(" " + pynini.union(*words))
        # The fractional digits shift left by the scale's zero count, so the padding
        # inserted after them follows the width that matched.
        shifted = pynini.union(
            *[
                (plain @ (DIGIT**width)) + pynutil.insert("0" * (zeros - width))
                for width in range(1, zeros + 1)
            ]
        )
        digits_1_3 = pynini.closure(DIGIT, 1, 3)
        graphs.append(
            (plain @ pynini.difference(digits_1_3, pynini.accep("0"))) + point + shifted + tail
        )
        # A zero integer part is dropped, not kept as a leading zero, and an all-zero
        # result collapses to a single 0.
        drop_zero = pynutil.delete((plain @ pynini.accep("0")).project("input"))
        all_zeros = pynini.accep("0" * zeros)
        graphs.append(
            drop_zero + point + (shifted @ pynini.difference(DIGIT**zeros, all_zeros)) + tail
        )
        graphs.append(drop_zero + point + (shifted @ pynini.cross("0" * zeros, "0")) + tail)
        # The fused half words scale the same way: ఒకటిన్నర వేలు -> 1500.
        if half_rows:
            graphs.append(
                pynini.union(
                    *[
                        pynini.cross(f"{fused} {word}", str(int(ip + fp.ljust(zeros, "0"))))
                        for fused, ip, fp in half_rows
                        for word in words
                    ]
                )
            )
    return pynini.union(*graphs).optimize()


class ItnCardinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken cardinals, e.g.
        ఇరవై మూడు -> cardinal { integer: "23" }
        రెండు వేల ఇరవై నాలుగులో -> cardinal { integer: "2024లో" }

    Attributes
    ----------
    tn_cardinal : ``CardinalBase``
        The language's TN cardinal, inverted here.
    pre_map : ``pynini.Fst``
        Rewrite normalizing spoken and colloquial number phrasing to the forms TN emits.
    extra_inverted : ``pynini.Fst | None``, optional (default = None)
        Further spoken-words-to-digits readings (an oblique scale word before a noun,
        hundreds of crores beyond the TN range); made unweighted here.
    suffix_exclusions : ``tuple[str, ...]``, optional (default = ())
        Written case suffixes that are ordinary plural markers on a bare number and so
        must not be carried into the digits (Telugu ల, లు).
    ambiguous_words : ``tuple[str, ...]``, optional (default = ())
        Number words that are just as often ordinary words (Malayalam ഒന്ന്, "just");
        alone they stay words, and convert only before a count noun or unit word.
    deterministic : ``bool``, optional (default = True)
        If True, provide a single transduction option.
    words_to_digits : ``pynini.Fst``
        Spoken number to ASCII digits, input-deterministic.
    words_to_digits_suffixed : ``pynini.Fst``
        The same with a written case suffix carried after the digits.
    """

    def __init__(
        self,
        tn_cardinal: CardinalBase,
        *,
        pre_map: pynini.Fst,
        extra_inverted: pynini.Fst | None = None,
        suffix_exclusions: tuple[str, ...] = (),
        ambiguous_words: tuple[str, ...] = (),
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="cardinal", kind="classify", deterministic=deterministic)

        profile = tn_cardinal.profile
        self.profile = profile
        to_ascii = profile.to_ascii
        # Every written form the TN grammar accepts, inverted and filtered to ASCII digits.
        inverted = (pynini.invert(tn_cardinal.itn_input_graph) @ to_ascii).optimize()
        if tn_cardinal.graph_year_hundreds is not None:
            inverted |= unweighted(pynini.invert(tn_cardinal.graph_year_hundreds) @ to_ascii)
        if extra_inverted is not None:
            inverted |= unweighted(extra_inverted)

        self.pre_map = pre_map
        plain = self.read(inverted)
        # A decimal amount times a small scale word is one number: ఐదు దశాంశం ఐదు వేలు -> 5500.
        self.words_to_digits = sequential(pynini.union(plain, _scale_expanded(profile, plain)))

        nouns_path = data_path(profile.lang, "numbers/count_nouns.tsv")
        nouns = {row[0] for row in load_labels(nouns_path)} if Path(nouns_path).exists() else set()
        unit_rows = load_labels(data_path(profile.lang, "measure/unit.tsv"), min_fields=2)
        graph = self.words_to_digits
        if ambiguous_words:
            ambiguous = pynini.union(*ambiguous_words)
            graph = pynini.compose(
                pynini.difference(pynini.project(graph, "input"), ambiguous), graph
            ).optimize()
            counted = pynini.union(*nouns, *[row[1] for row in unit_rows])
            graph |= (
                (ambiguous @ self.words_to_digits) + " " + counted + pynini.closure(profile.letter)
            )
        else:
            graph = graph.copy()
        if profile.case_suffixes:
            # A case suffix on the last number word is carried into the written form.
            # Vowel-sign suffixes are left out: ఒకటే is an ordinary word, not 1ే.
            kept_letters = pynini.closure(profile.letter)
            if suffix_exclusions:
                kept_letters = pynini.difference(kept_letters, pynini.union(*suffix_exclusions))
            keep_suffix = to_ascii + kept_letters
            suffixed = (
                pynini.invert(
                    tn_cardinal.attach_case_suffix(
                        tn_cardinal.readable_years(), include_vowel=False
                    )
                )
                @ keep_suffix
            ).optimize()
            self.words_to_digits_suffixed = self.read(suffixed)
            graph |= pynutil.add_weight(self.words_to_digits_suffixed, 0.1)
        else:
            self.words_to_digits_suffixed = pynini.Fst()

        if profile.counting_one:
            # The counting one reads as 1 before a unit word only (ఒక కిలోగ్రామ్ -> 1
            # కిలోగ్రామ్); before any other noun it is also the article and stays. A unit
            # that is also an ordinary count noun (గంట) is left out for the same reason.
            units = [row[1] for row in unit_rows if row[1] not in nouns]
            one_unit = (
                pynini.cross(profile.counting_one, "1")
                + " "
                + pynini.union(*units)
                + pynini.closure(profile.letter)
            )
            graph |= pynutil.add_weight(one_unit, 0.1)

        graph = (
            optional_sign_field(profile)
            + pynutil.insert('integer: "')
            + graph
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()

    def read(self, lexicon: pynini.Fst) -> pynini.Fst:
        """
        Read spoken words through the pre-map into ``lexicon``, input-deterministically.
        """
        return sequential(self.pre_map @ lexicon)
