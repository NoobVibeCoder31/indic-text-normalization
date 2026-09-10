"""
Telugu spoken-number normalization for ITN: the variant pre-map and the readings beyond
the TN cardinal's range.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import DIGIT, SIGMA, unweighted
from indic_text_normalization.te.morphology import OBLIQUE_FINAL
from indic_text_normalization.te.tn.taggers.cardinal import CardinalFst as TnCardinalFst

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
    ("ఒకటీ", "ఒకటి"),
    ("ఎనిమ్మిది", "ఎనిమిది"),
    ("సున్న", "సున్నా"),
    # English loanword for zero, common in ASR output.
    ("జీరో", "సున్నా"),
    ("వేయి", "వెయ్యి"),
    ("వెయ్యీ", "వెయ్యి"),
    ("లక్షం", "లక్ష"),
    ("లక్షా", "లక్ష"),
    ("నూరు", "వంద"),
    ("నూటా", "నూట"),
    ("వందా", "నూట"),
    ("వేలా", "వేల"),
    ("కోటీ", "కోటి"),
    # Classical contracted hundreds, alongside the colloquial -ొందలు forms below.
    ("ఇన్నూరు", "రెండు వందలు"),
    ("మున్నూరు", "మూడు వందలు"),
    ("నానూరు", "నాలుగు వందలు"),
    ("ఐనూరు", "ఐదు వందలు"),
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
_TENS_STEMS = ["ఇరవ", "ముప్ప", "నలభ", "యాభ", "అరవ", "డెబ్బ", "ఎనభ", "తొంభ"]
_CONSONANT_DIGITS = ["రెండు", "మూడు", "నాలుగు", "ఏడు", "తొమ్మిది"]
_VOWEL_DIGITS = ["ఒకటి", "ఐదు", "ఆరు", "ఎనిమిది"]
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
        pynutil.insert(" "),
        edge + stems + "ై",
        pynini.union(*_CONSONANT_DIGITS, *_VOWEL_DIGITS),
        SIGMA,
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


def _hundreds_of_crores(tn_cardinal: TnCardinalFst, to_ascii: pynini.Fst) -> pynini.Fst:
    """
    Read 100-999 crore, one place beyond the TN cardinal: ఐదు వందల కోట్లు -> 5000000000,
    ఐదు వందల కోట్ల నలభై ఐదు లక్షలు -> 5004500000.
    """
    # The hundreds word stands in its oblique before కోట్లు (ఐదు వందల కోట్లు, నూట ఐదు కోట్లు).
    hundreds = unweighted(pynini.invert(tn_cardinal.graph_hundreds @ OBLIQUE_FINAL) @ to_ascii)
    below_crore = unweighted(
        pynini.invert(
            pynini.union(
                tn_cardinal.digit,
                tn_cardinal.teens_and_ties,
                tn_cardinal.graph_hundreds,
                tn_cardinal.graph_thousands,
                tn_cardinal.graph_ten_thousands,
                tn_cardinal.graph_lakhs,
                tn_cardinal.graph_ten_lakhs,
            )
        )
        @ to_ascii
    )
    remainder = pynini.union(
        *[pynutil.insert("0" * (7 - width)) + (below_crore @ DIGIT**width) for width in range(1, 8)]
    )
    exact = hundreds + pynini.cross(" " + pynini.union("కోట్లు", "కోట్ల"), "0000000")
    return pynini.union(exact, hundreds + pynutil.delete(" కోట్ల ") + remainder).optimize()


def extra_inverted(tn_cardinal: TnCardinalFst) -> pynini.Fst:
    """
    Spoken readings the inverted TN cardinal lacks: a plural scale word in its oblique
    form before a noun (రెండు వేల రూపాయలు) and hundreds of crores.
    """
    to_ascii = tn_cardinal.profile.to_ascii
    oblique = tn_cardinal.final_graph @ (SIGMA + pynini.cross("లు", "ల"))
    return pynini.union(
        pynini.invert(oblique) @ to_ascii, _hundreds_of_crores(tn_cardinal, to_ascii)
    ).optimize()
