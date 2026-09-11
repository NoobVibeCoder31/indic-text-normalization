"""
Hindi spoken-number normalization for ITN: the variant pre-map and the readings the TN
cardinal does not emit.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA
from indic_text_normalization.hi.tn.taggers.cardinal import CardinalFst as TnCardinalFst

# Spelling variants ITN accepts and the form the TN grammar emits: anusvara for
# chandrabindu, a missing nukta, regional spellings.
VARIANTS = [
    ("पांच", "पाँच"),
    ("पाच", "पाँच"),
    ("छः", "छह"),
    ("छे", "छह"),
    ("छ", "छह"),
    ("हजार", "हज़ार"),
    ("हज़ारों", "हज़ार"),
    ("हजारों", "हज़ार"),
    ("करोड", "करोड़"),
    ("करोड़ों", "करोड़"),
    ("लाखों", "लाख"),
    ("सैकड़ों", "सौ"),
    ("अठारा", "अठारह"),
    ("उन्निस", "उन्नीस"),
    ("इक्किस", "इक्कीस"),
    ("बाइस", "बाईस"),
    ("तेइस", "तेईस"),
    ("सताईस", "सत्ताईस"),
    ("अठाईस", "अट्ठाईस"),
    ("अठ्ठाईस", "अट्ठाईस"),
    ("उन्तीस", "उनतीस"),
    ("बतीस", "बत्तीस"),
    ("तैतीस", "तैंतीस"),
    ("चौतीस", "चौंतीस"),
    ("पैतीस", "पैंतीस"),
    ("छतीस", "छत्तीस"),
    ("सैतीस", "सैंतीस"),
    ("अडतीस", "अड़तीस"),
    ("उन्तालीस", "उनतालीस"),
    ("एकतालीस", "इकतालीस"),
    ("बियालीस", "बयालीस"),
    ("तैतालीस", "तैंतालीस"),
    ("चौवालीस", "चवालीस"),
    ("पैतालीस", "पैंतालीस"),
    ("छयालीस", "छियालीस"),
    ("सैतालीस", "सैंतालीस"),
    ("अडतालीस", "अड़तालीस"),
    ("उन्चास", "उनचास"),
    ("इकावन", "इक्यावन"),
    ("तिरेपन", "तिरपन"),
    ("सतावन", "सत्तावन"),
    ("अठावन", "अट्ठावन"),
    ("उन्सठ", "उनसठ"),
    ("तिरेसठ", "तिरसठ"),
    ("चौसठ", "चौंसठ"),
    ("पैसठ", "पैंसठ"),
    ("छयासठ", "छियासठ"),
    ("सरसठ", "सड़सठ"),
    ("अडसठ", "अड़सठ"),
    ("उन्हत्तर", "उनहत्तर"),
    ("उन्यासी", "उनासी"),
    ("इकासी", "इक्यासी"),
    ("सतासी", "सत्तासी"),
    ("अठासी", "अट्ठासी"),
    ("इक्यानबे", "इक्यानवे"),
    ("बानबे", "बानवे"),
    ("तिरानबे", "तिरानवे"),
    ("चौरानबे", "चौरानवे"),
    ("पचानबे", "पचानवे"),
    ("छियानबे", "छियानवे"),
    ("सत्तानबे", "सत्तानवे"),
    ("अट्ठानबे", "अट्ठानवे"),
    ("निन्यानबे", "निन्यानवे"),
    ("ज़ीरो", "शून्य"),
    ("जीरो", "शून्य"),
    ("सिफ़र", "शून्य"),
    ("सिफर", "शून्य"),
]


# Variants inside a word: the ordinal पांचवां for पाँचवाँ.
PREFIX_VARIANTS = [("पांच", "पाँच")]
SUFFIX_VARIANTS = [("वां", "वाँ")]


def spoken_pre_map() -> pynini.Fst:
    """
    Normalize spoken and colloquial number phrasing to the forms the TN grammar emits.
    """
    edge = pynini.union("[BOS]", " ")
    right = pynini.union("[EOS]", " ")
    variants = (
        pynini.cdrewrite(
            pynini.union(*[pynini.cross(a, b) for a, b in VARIANTS]), edge, right, SIGMA
        )
        @ pynini.cdrewrite(
            pynini.union(*[pynini.cross(a, b) for a, b in PREFIX_VARIANTS]), edge, "", SIGMA
        )
        @ pynini.cdrewrite(
            pynini.union(*[pynini.cross(a, b) for a, b in SUFFIX_VARIANTS]), "", right, SIGMA
        )
    )
    # A bare सौ or हज़ार counts one: सौ बीस -> एक सौ बीस, हज़ार -> एक हज़ार.
    bare_one = pynini.cdrewrite(
        pynutil.insert("एक "), "[BOS]", pynini.union("सौ", "हज़ार") + right, SIGMA
    )
    return (variants @ bare_one).optimize()


def extra_inverted(tn_cardinal: TnCardinalFst) -> pynini.Fst:
    """
    Nothing beyond the inverted TN cardinal and its hundreds-style years.
    """
    del tn_cardinal
    return pynini.Fst()
