"""
ITN tagger converting spoken Tamil numbers to ASCII digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.ta.constants import (
    CHAR,
    DIGIT,
    SIGMA,
    TA_TO_ASCII_DIGIT,
    GraphFst,
)
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst as TnCardinalFst
from indic_text_normalization.ta.utils import get_abs_path

# Colloquial (spoken/ASR) forms rewritten to the formal words the grammar knows.
_COLLOQUIAL = [
    ("ஒன்னு", "ஒன்று"),
    ("ஒண்ணு", "ஒன்று"),
    ("ரெண்டு", "இரண்டு"),
    ("மூணு", "மூன்று"),
    ("நாலு", "நான்கு"),
    ("அஞ்சு", "ஐந்து"),
    ("ஒம்பது", "ஒன்பது"),
    ("பன்னெண்டு", "பன்னிரண்டு"),
    ("பன்னிரெண்டு", "பன்னிரண்டு"),
    ("அம்பது", "ஐம்பது"),
    ("ஐநூறு", "ஐந்நூறு"),
]

# Colloquial/formal -த்தி tens joints normalized to the -த்து stems.
_TENS_JOINTS = [
    ("இருவத்தி", "இருபத்து"),
    ("இருபத்தி", "இருபத்து"),
    ("முப்பத்தி", "முப்பத்து"),
    ("நாப்பத்தி", "நாற்பத்து"),
    ("நாற்பத்தி", "நாற்பத்து"),
    ("அம்பத்தி", "ஐம்பத்து"),
    ("ஐம்பத்தி", "ஐம்பத்து"),
    ("அறுபத்தி", "அறுபத்து"),
    ("எழுபத்தி", "எழுபத்து"),
    ("எண்பத்தி", "எண்பத்து"),
    ("தொண்ணூத்தி", "தொண்ணூற்று"),
    ("தொண்ணூற்றி", "தொண்ணூற்று"),
    ("நூத்தி", "நூற்று"),
    ("இருநூத்தி", "இருநூற்று"),
    ("முன்னூத்தி", "முந்நூற்று"),
    ("ஆயிரத்தி", "ஆயிரத்து"),
    ("ரெண்டாயிர", "இரண்டாயிர"),
    ("மூணாயிர", "மூன்றாயிர"),
]

_TENS_STEMS = [
    "இருபத்து",
    "முப்பத்து",
    "நாற்பத்து",
    "ஐம்பத்து",
    "அறுபத்து",
    "எழுபத்து",
    "எண்பத்து",
    "தொண்ணூற்று",
]

_DIGIT_WORDS = ["ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து", "ஆறு", "ஏழு", "எட்டு", "ஒன்பது"]


def _boundary_rewrite(pairs: list[tuple[str, str]]) -> pynini.Fst:
    """
    Word-boundary-anchored rewrite for the given (spoken, formal) pairs.
    """
    tau = pynini.union(*[pynini.cross(a, b) for a, b in pairs])
    edge = pynini.union("[BOS]", " ")
    right = pynini.union("[EOS]", " ")
    return pynini.cdrewrite(tau, edge, right, SIGMA).optimize()


def _spoken_pre_map() -> pynini.Fst:
    """
    Normalize spoken/colloquial number phrasing to the forms the TN grammar emits.
    """
    edge = pynini.union("[BOS]", " ")
    colloquial = _boundary_rewrite(_COLLOQUIAL)
    joints = pynini.cdrewrite(
        pynini.union(*[pynini.cross(a, b) for a, b in _TENS_JOINTS]), edge, "", SIGMA
    )
    scale_links = _boundary_rewrite(
        [
            ("கோடியே", "கோடி"),
            ("இலட்சத்து", "இலட்சம்"),
            ("லட்சத்து", "இலட்சம்"),
            ("லட்சம்", "இலட்சம்"),
            ("ஓராயிரம்", "ஆயிரம்"),
            ("ஓர் ஆயிரம்", "ஆயிரம்"),
        ]
    )
    # Fused thousands split back to the spaced reading: அறுபதாயிரம் -> அறுபது ஆயிரம்.
    # தொள்ளாயிரம் (900) also contains ாயிரம், so a ள just before blocks the split.
    split_thousands = pynini.cdrewrite(
        pynini.union(pynini.cross("ாயிரத்து", "ு ஆயிரம்"), pynini.cross("ாயிரம்", "ு ஆயிரம்")),
        pynini.difference(CHAR, pynini.accep("ள")),
        "",
        SIGMA,
    )
    # Colloquial -ஞ்சு endings after த/ன read as -ைந்து (பதினஞ்சு -> பதினைந்து).
    nju = pynini.cdrewrite(
        pynini.cross("ஞ்சு", "ைந்து"), pynini.union("த", "ன"), pynini.union("[EOS]", " "), SIGMA
    )
    # A spaced tens+digit pair joins into the fused sandhi form the grammar
    # accepts: consonant-initial digits join directly, vowel-initial digits
    # merge the tens-final ு with their initial vowel (நாற்பத்து ஒன்று -> நாற்பத்தொன்று).
    stems_lopped = pynini.union(*[stem[:-1] for stem in _TENS_STEMS])
    join_consonant = pynini.cdrewrite(
        pynutil.delete(" "),
        edge + pynini.union(*_TENS_STEMS),
        pynini.union("மூன்று", "நான்கு"),
        SIGMA,
    )
    vowel_merge = pynini.union(
        pynini.cross("ு ஒ", "ொ"),
        pynini.cross("ு இ", "ி"),
        pynini.cross("ு எ", "ெ"),
        pynini.cross("ு ஏ", "ே"),
        pynini.cross("ு ஐ", "ை"),
        pynini.cross("ு ஆ", "ா"),
    )
    join_vowel = pynini.cdrewrite(vowel_merge, edge + stems_lopped, "", SIGMA)
    return (
        colloquial @ nju @ joints @ scale_links @ split_thousands @ join_consonant @ join_vowel
    ).optimize()


class CardinalFst(GraphFst):
    """
    Finite state transducer for classifying spoken cardinals, e.g.
        இருபத்துமூன்று -> cardinal { integer: "23" }
        ரெண்டு -> cardinal { integer: "2" }
    """

    def __init__(self, tn_cardinal: TnCardinalFst, deterministic: bool = True) -> None:
        super().__init__(name="cardinal", kind="classify", deterministic=deterministic)

        # Every written form the TN grammar accepts, inverted and filtered to ASCII digits.
        # The TN grammar emits a leading space before நூற்று forms, so allow inserting one.
        to_ascii = pynini.closure(pynini.union(TA_TO_ASCII_DIGIT, DIGIT))
        optional_leading_space = pynini.closure(pynutil.insert(" "), 0, 1) + pynini.closure(CHAR)
        inverted = (
            optional_leading_space @ pynini.invert(tn_cardinal.itn_input_graph) @ to_ascii
        ).optimize()

        # Spoken variants with spaced compounds, adapted from indic-num2words.
        variants = pynini.string_file(get_abs_path("data/numbers/itn_variants.tsv")).optimize()

        self.words_to_digits = (_spoken_pre_map() @ (inverted | variants)).optimize()

        optional_minus = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("மைனஸ் ", '"true" '), 0, 1
        )

        graph = (
            optional_minus
            + pynutil.insert('integer: "')
            + self.words_to_digits
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()
