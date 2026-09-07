"""
ITN tagger converting spoken Telugu numbers to ASCII digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.te.constants import (
    DIGIT,
    MINUS_WORD,
    SIGMA,
    TE_LETTER,
    TE_TO_ASCII_DIGIT,
    GraphFst,
)
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst as TnCardinalFst
from indic_text_normalization.te.tn.taggers.cardinal import attach_case_suffix
from indic_text_normalization.te.utils import get_abs_path

# Spelling, dialect and ASR variants rewritten to the words the TN grammar emits.
_VARIANTS = [
    ("పంతొమ్మిది", "పందొమ్మిది"),
    ("పదహైదు", "పదిహేను"),
    ("పదిహైదు", "పదిహేను"),
    ("పదహేను", "పదిహేను"),
    ("పధ్నాలుగు", "పద్నాలుగు"),
    ("పదునాలుగు", "పద్నాలుగు"),
    ("పదునెనిమిది", "పద్దెనిమిది"),
    ("పదెనిమిది", "పద్దెనిమిది"),
    ("ముప్పది", "ముప్పై"),
    ("ముప్ఫై", "ముప్పై"),
    ("నలుబది", "నలభై"),
    ("నలబై", "నలభై"),
    ("యాబది", "యాభై"),
    ("యాబై", "యాభై"),
    ("ఏభై", "యాభై"),
    ("అరువది", "అరవై"),
    ("ఆరవై", "అరవై"),
    ("డెబ్భై", "డెబ్బై"),
    ("డెబ్బది", "డెబ్బై"),
    ("ఎనబై", "ఎనభై"),
    ("ఎనభది", "ఎనభై"),
    ("తొంబై", "తొంభై"),
    ("తొంబది", "తొంభై"),
    ("అయిదు", "ఐదు"),
    ("ఒక్కటి", "ఒకటి"),
    ("ఎనిమ్మిది", "ఎనిమిది"),
    ("సున్న", "సున్నా"),
    ("వేయి", "వెయ్యి"),
    ("వెయ్యీ", "వెయ్యి"),
    ("లక్షం", "లక్ష"),
    ("లక్షా", "లక్ష"),
    ("నూరు", "వంద"),
    ("నూటా", "నూట"),
    ("వందా", "నూట"),
    ("వేలా", "వేల"),
    ("కోటీ", "కోటి"),
    ("రెండొందలు", "రెండు వందలు"),
    ("రెండొందల", "రెండు వందల"),
    ("మూడొందలు", "మూడు వందలు"),
    ("మూడొందల", "మూడు వందల"),
    ("నాలుగొందలు", "నాలుగు వందలు"),
    ("నాలుగొందల", "నాలుగు వందల"),
    ("ఐదొందలు", "ఐదు వందలు"),
    ("ఐదొందల", "ఐదు వందల"),
    ("ఆరొందలు", "ఆరు వందలు"),
    ("ఆరొందల", "ఆరు వందల"),
    ("ఏడొందలు", "ఏడు వందలు"),
    ("ఏడొందల", "ఏడు వందల"),
    ("ఎనిమిదొందలు", "ఎనిమిది వందలు"),
    ("ఎనిమిదొందల", "ఎనిమిది వందల"),
    ("తొమ్మిదొందలు", "తొమ్మిది వందలు"),
    ("తొమ్మిదొందల", "తొమ్మిది వందల"),
]

# Spoken negative words folded to the TN sign word.
NEGATIVE_WORDS = [MINUS_WORD, "మైనస్", "రుణ", "ఋణాత్మక", "రుణాత్మక"]

_TENS_STEMS = ["ఇరవ", "ముప్ప", "నలభ", "యాభ", "అరవ", "డెబ్బ", "ఎనభ", "తొంభ"]
_CONSONANT_DIGITS = ["రెండు", "మూడు", "నాలుగు", "ఏడు", "తొమ్మిది"]
_SCALE_WORDS = ["వంద", "వెయ్యి", "లక్ష", "కోటి"]
_GLUED_SCALES = ["వందలు", "వందల", "వేలు", "వేల", "వేలా", "లక్షలు", "లక్షల", "కోట్లు", "కోట్ల"]
_TENS_WORDS = ["పది", "ఇరవై", "ముప్పై", "నలభై", "యాభై", "అరవై", "డెబ్బై", "ఎనభై", "తొంభై"]


def _boundary_rewrite(pairs: list[tuple[str, str]]) -> pynini.Fst:
    """
    Word-boundary-anchored rewrite for the given (spoken, formal) pairs.
    """
    tau = pynini.union(*[pynini.cross(a, b) for a, b in pairs])
    edge = pynini.union("[BOS]", " ")
    right = pynini.union("[EOS]", " ")
    return pynini.cdrewrite(tau, edge, right, SIGMA).optimize()


def spoken_pre_map() -> pynini.Fst:
    """
    Normalize spoken/colloquial number phrasing to the forms the TN grammar emits.
    """
    edge = pynini.union("[BOS]", " ")
    variants = _boundary_rewrite(_VARIANTS)
    # Fused tens + units split back to the spaced reading: ఇరవైరెండు -> ఇరవై రెండు,
    # ఇరవయ్యొకటి -> ఇరవై ఒకటి.
    stems = pynini.union(*_TENS_STEMS)
    split_consonant = pynini.cdrewrite(
        pynutil.insert(" "), edge + stems + "ై", pynini.union(*_CONSONANT_DIGITS), SIGMA
    )
    split_vowel = pynini.cdrewrite(
        pynini.union(
            pynini.cross("య్యొ", "ై ఒ"),
            pynini.cross("య్యై", "ై ఐ"),
            pynini.cross("య్యా", "ై ఆ"),
            pynini.cross("య్యె", "ై ఎ"),
        ),
        edge + stems,
        "",
        SIGMA,
    )
    # A scale word glued to its multiplier is split (రెండువేలు -> రెండు వేలు), and a
    # remainder glued to నూట likewise (నూటయాభై -> నూట యాభై, నూటొకటి -> నూట ఒకటి).
    letter = pynini.union(*[chr(i) for i in range(0x0C05, 0x0C57)])
    split_scale = pynini.cdrewrite(
        pynutil.insert(" "),
        letter,
        pynini.union(*_GLUED_SCALES) + pynini.union("[EOS]", " "),
        SIGMA,
    )
    split_hundred = pynini.cdrewrite(
        pynini.union(
            pynutil.insert(" "),
        ),
        edge + "నూట",
        pynini.union(*_TENS_WORDS, *_CONSONANT_DIGITS),
        SIGMA,
    )
    split_hundred_vowel = pynini.cdrewrite(
        pynini.union(
            pynini.cross("ొ", " ఒ"),
            pynini.cross("ై", " ఐ"),
            pynini.cross("ా", " ఆ"),
            pynini.cross("ె", " ఎ"),
        ),
        edge + "నూట",
        "",
        SIGMA,
    )
    # వంద followed directly by a tens or units word is the 1xx idiom (వంద యాభై -> నూట యాభై).
    hundred_idiom = pynini.cdrewrite(
        pynini.cross("వంద", "నూట"),
        edge,
        " " + pynini.union(*_TENS_WORDS, *_CONSONANT_DIGITS, "ఒకటి", "ఐదు", "ఆరు", "ఎనిమిది"),
        SIGMA,
    )
    # A counting ఒక before a bare scale word is silent in the TN reading (ఒక లక్ష -> లక్ష).
    drop_oka = pynini.cdrewrite(
        pynutil.delete("ఒక "), edge, pynini.union(*_SCALE_WORDS) + pynini.union("[EOS]", " "), SIGMA
    )
    return (
        variants
        @ split_scale
        @ split_hundred
        @ split_hundred_vowel
        @ hundred_idiom
        @ split_consonant
        @ split_vowel
        @ drop_oka
    ).optimize()


class CardinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken cardinals, e.g.
        ఇరవై మూడు -> cardinal { integer: "23" }
        రెండు వేల ఇరవై నాలుగులో -> cardinal { integer: "2024లో" }
    """

    def __init__(self, tn_cardinal: TnCardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="cardinal", kind="classify", deterministic=deterministic)

        to_ascii = pynini.closure(pynini.union(TE_TO_ASCII_DIGIT, DIGIT))
        # Every written form the TN grammar accepts, inverted and filtered to ASCII digits.
        inverted = (pynini.invert(tn_cardinal.itn_input_graph) @ to_ascii).optimize()
        # A plural scale word closing the phrase may stand in its oblique form before a
        # noun (రెండు వేల రూపాయలు), and years 1100-1999 read as hundreds.
        oblique = tn_cardinal.final_graph @ (SIGMA + pynini.cross("లు", "ల"))
        inverted |= (pynini.invert(oblique) @ to_ascii).optimize()
        inverted |= (pynini.invert(tn_cardinal.graph_year_hundreds) @ to_ascii).optimize()

        # Whole-phrase synonyms (నూరు, ఒక వంద, ఇన్నూరు ...).
        variants = pynini.string_file(get_abs_path("data/numbers/itn_variants.tsv")).optimize()

        self.pre_map = spoken_pre_map()
        self.words_to_digits = (self.pre_map @ (inverted | variants)).optimize()

        # A case suffix on the last number word is carried into the written form. Vowel-sign
        # suffixes are left out: ఒకటే is an ordinary word, not 1ే.
        # A bare plural marker ల is not a suffix here: వేల / లక్షల alone are generic plurals.
        keep_suffix = to_ascii + pynini.difference(
            pynini.closure(TE_LETTER), pynini.union("ల", "లు")
        )
        suffixable = pynini.union(
            tn_cardinal.final_graph, tn_cardinal.graph_year_hundreds
        ).optimize()
        suffixed = (
            pynini.invert(attach_case_suffix(suffixable, include_vowel=False)) @ keep_suffix
        ).optimize()
        self.words_to_digits_suffixed = (self.pre_map @ suffixed).optimize()

        negative = pynini.union(*[pynini.cross(w + " ", '"true" ') for w in NEGATIVE_WORDS])
        optional_minus = pynini.closure(pynutil.insert("negative: ") + negative, 0, 1)

        graph = (
            optional_minus
            + pynutil.insert('integer: "')
            + (self.words_to_digits | pynutil.add_weight(self.words_to_digits_suffixed, 0.1))
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()
