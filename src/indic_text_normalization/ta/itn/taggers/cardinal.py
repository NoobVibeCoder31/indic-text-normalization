"""
ITN tagger converting spoken Tamil numbers to ASCII digits.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import CHAR, DIGIT, GraphFst, sequential, SIGMA
from indic_text_normalization.ta.constants import (
    LANG,
    MINUS_WORD,
    PLUS_WORD,
    TA_LETTER,
    TA_TO_ASCII_DIGIT,
)
from indic_text_normalization.ta.itn.ambiguity import LICENSED, ambiguous_words
from indic_text_normalization.ta.itn.fused import half_form_rows
from indic_text_normalization.core.scales import expanded_scale_words
from indic_text_normalization.ta.tn.taggers.cardinal import CardinalFst as TnCardinalFst

# Colloquial (spoken/ASR) forms rewritten to the formal words the grammar knows.
_COLLOQUIAL = [
    ("ஒன்னு", "ஒன்று"),
    ("ஒண்ணு", "ஒன்று"),
    ("ரெண்டு", "இரண்டு"),
    ("மூணு", "மூன்று"),
    ("நாலு", "நான்கு"),
    ("அஞ்சு", "ஐந்து"),
    ("ஒம்பது", "ஒன்பது"),
    ("பூஜ்ஜியம்", "பூஜ்யம்"),
    ("பன்னெண்டு", "பன்னிரண்டு"),
    ("பன்னிரெண்டு", "பன்னிரண்டு"),
    ("அம்பது", "ஐம்பது"),
    ("ஐநூறு", "ஐந்நூறு"),
    # U+0BA9 TAMIL LETTER NNA spelling of 300 (முந்நூறு is the grammar's form).
    ("முன்னூறு", "முந்நூறு"),
    # U+0BA9 TAMIL LETTER NNA misspelling of 90 (தொண்ணூறு is the grammar's form).
    ("தொன்ணூறு", "தொண்ணூறு"),
    ("முன்னூற்று", "முந்நூற்று"),
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
    ("முன்னூற்றி", "முந்நூற்று"),
    ("ஆயிரத்தி", "ஆயிரத்து"),
    ("ரெண்டாயிர", "இரண்டாயிர"),
    ("மூணாயிர", "மூன்றாயிர"),
]

# Compound linkers and scale-word spellings normalized to the grammar's own forms.
_SCALE_LINKS = [
    ("கோடியே", "கோடி"),
    ("இலட்சத்து", "இலட்சம்"),
    ("லட்சத்து", "இலட்சம்"),
    ("லட்சம்", "இலட்சம்"),
    ("ஓராயிரம்", "ஆயிரம்"),
    ("ஓர் ஆயிரம்", "ஆயிரம்"),
    ("ஒரு ஆயிரம்", "ஆயிரம்"),
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


# Dependent vowel sign paired with the independent vowel it stands for, used both to
# fuse a spaced tens+digit pair and to split a solid one back apart.
_VOWEL_SIGNS = [("ொ", "ஒ"), ("ி", "இ"), ("ெ", "எ"), ("ே", "ஏ"), ("ை", "ஐ"), ("ா", "ஆ")]
_VOWELS = [vowel for _, vowel in _VOWEL_SIGNS]


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
    scale_links = _boundary_rewrite(_SCALE_LINKS)
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
    # A -தி joint written solid onto a vowel-initial digit takes a ய glide
    # (எண்பத்தியொன்று) or fuses ந to ன (எண்பத்தினான்கு); split it back to the spaced
    # reading so the joining stages below can rebuild the grammar's own sandhi form.
    stems = pynini.union(*_TENS_STEMS)
    glide_split = pynini.union(
        *[pynini.cross(f"ய{sign}", f" {vowel}") for sign, vowel in _VOWEL_SIGNS]
    )
    unfuse = (
        pynini.cdrewrite(glide_split, stems, "", SIGMA)
        @ pynini.cdrewrite(pynini.cross("ன", " ந"), stems, "ா", SIGMA)
        @ pynini.cdrewrite(pynutil.insert(" "), stems, pynini.union(*_VOWELS), SIGMA)
    )

    # A spaced tens+digit pair joins into the fused sandhi form the grammar
    # accepts: consonant-initial digits join directly, vowel-initial digits
    # merge the tens-final ு with their initial vowel (நாற்பத்து ஒன்று -> நாற்பத்தொன்று).
    stems_lopped = pynini.union(*[stem[:-1] for stem in _TENS_STEMS])
    join_consonant = pynini.cdrewrite(
        pynutil.delete(" "),
        edge + stems,
        pynini.union("மூன்று", "நான்கு"),
        SIGMA,
    )
    vowel_merge = pynini.union(*[pynini.cross(f"ு {vowel}", sign) for sign, vowel in _VOWEL_SIGNS])
    join_vowel = pynini.cdrewrite(vowel_merge, edge + stems_lopped, "", SIGMA)
    return (
        colloquial
        @ nju
        @ joints
        @ unfuse
        @ scale_links
        @ split_thousands
        @ join_consonant
        @ join_vowel
    ).optimize()


def _pre_map_domain() -> pynini.Fst:
    """
    Strings some pre-map stage can rewrite; the chain is the identity on anything else,
    which the raw reading already covers.
    """
    triggers = (
        [spoken for spoken, _ in _COLLOQUIAL + _TENS_JOINTS + _SCALE_LINKS]
        + _TENS_STEMS
        + ["ஞ்சு", "ாயிரத்து", "ாயிரம்"]
        + [f"ு {vowel}" for vowel in ("ஒ", "இ", "எ", "ஏ", "ஐ", "ஆ")]
    )
    return (pynini.closure(CHAR) + pynini.union(*triggers) + pynini.closure(CHAR)).optimize()


def _hundreds_split() -> pynini.Fst:
    """
    Split the spoken hundreds sandhi back into the spaced form: நூற்றிரண்டு -> நூற்று இரண்டு.
    """
    signs = ["ி", "ொ", "ெ", "ே", "ை", "ா"]
    vowels = ["இ", "ஒ", "எ", "ஏ", "ஐ", "ஆ"]
    stems = pynini.union("நூற்ற", "ஆயிரத்த")
    unmerge = pynini.union(*[pynini.cross(s, f"ு {v}") for s, v in zip(signs, vowels, strict=True)])
    rewrite = pynini.cdrewrite(unmerge, stems, "", SIGMA)
    # Restricted to strings that actually carry the sandhi, so this second reading of
    # the input costs a small composition instead of a whole extra copy of the grammar.
    domain = (pynini.closure(CHAR) + stems + pynini.union(*signs) + pynini.closure(CHAR)).optimize()
    return pynini.compose(domain, rewrite).optimize()


def _scale_expanded(plain: pynini.Fst) -> pynini.Fst:
    """
    Multiply out a scale word small enough for it, e.g. ஐந்து புள்ளி ஐந்து ஆயிரம் -> 5500.
    """
    graphs = []
    for word, zeros in expanded_scale_words(LANG):
        # The fractional digits shift left by the scale's zero count, so the padding
        # inserted after them follows the width that matched.
        shifted = pynini.union(
            *[
                (plain @ (DIGIT**width)) + pynutil.insert("0" * (zeros - width))
                for width in range(1, zeros + 1)
            ]
        )
        digits_1_3 = pynini.closure(DIGIT, 1, 3)
        point, tail = pynutil.delete(" புள்ளி "), pynutil.delete(f" {word}")
        graphs.append(
            (plain @ pynini.difference(digits_1_3, pynini.accep("0"))) + point + shifted + tail
        )
        # A zero integer part is dropped, not kept as a leading zero: பூஜ்யம் புள்ளி ஐந்து
        # ஆயிரம் is 500, and an all-zero result collapses to a single 0.
        drop_zero = pynutil.delete((plain @ pynini.accep("0")).project("input"))
        all_zeros = pynini.accep("0" * zeros)
        graphs.append(
            drop_zero + point + (shifted @ pynini.difference(DIGIT**zeros, all_zeros)) + tail
        )
        graphs.append(drop_zero + point + (shifted @ pynini.cross("0" * zeros, "0")) + tail)
        # The fused half/quarter words scale the same way: ஒன்றரை ஆயிரம் -> 1500.
        graphs.append(
            pynini.union(
                *[
                    pynini.cross(f"{fused} {word}", str(int(ip + fp.ljust(zeros, "0"))))
                    for fused, ip, fp in half_form_rows()
                ]
            )
        )
    return pynini.union(*graphs).optimize()


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
        inverted = sequential(
            optional_leading_space @ pynini.invert(tn_cardinal.itn_input_graph) @ to_ascii
        )

        # The pre-map rewrites colloquial phrasing but would destroy the sandhi forms
        # TN itself emits (இருபத்திரண்டு), so the raw input is tried first.
        # Restricted to the strings it can actually change, so the colloquial reading costs
        # a small composition instead of a second copy of the whole number grammar.
        pre_map = pynini.compose(_pre_map_domain(), _spoken_pre_map()).optimize()
        accepted = inverted
        plain = sequential(
            pynini.union(
                pynutil.add_weight(accepted, -0.01),
                pre_map @ accepted,
                _hundreds_split() @ accepted,
            )
        )
        self.words_to_digits = sequential(pynini.union(plain, _scale_expanded(plain)))

        # ஒரு / ஓர் are also the indefinite article, so they count as numbers only
        # where a currency, unit or clock word makes the numeric reading explicit.
        articles = pynini.string_map(ambiguous_words(LICENSED)).optimize()
        self.words_to_digits_with_article = sequential(pynini.union(self.words_to_digits, articles))

        # Case-suffixed numbers keep their suffix: இரண்டாயிரத்து இருபத்துநான்கில் -> 2024ல்.
        suffixed_out = pynini.closure(pynini.union(TA_TO_ASCII_DIGIT, DIGIT), 1) + pynini.closure(
            TA_LETTER, 1
        )
        inverted_suffixed = sequential(pynini.invert(tn_cardinal.itn_suffixed_graph) @ suffixed_out)
        self.suffixed_words_to_digits = sequential(
            pynini.union(pynutil.add_weight(inverted_suffixed, -0.01), pre_map @ inverted_suffixed)
        )

        optional_sign = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross(f"{MINUS_WORD} ", '"true" ')
            | pynutil.insert("positive: ") + pynini.cross(f"{PLUS_WORD} ", '"true" '),
            0,
            1,
        )

        graph = (
            optional_sign
            + pynutil.insert('integer: "')
            + (self.words_to_digits | pynutil.add_weight(self.suffixed_words_to_digits, 0.05))
            + pynutil.insert('"')
        )
        self.fst = self.add_tokens(graph).optimize()
