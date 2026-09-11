"""
Telugu noun morphology shared by the TN verbalizers: plural/oblique scale words, the
counting-one ఒక, and case-suffix sandhi on the noun a number modifies.
"""

import functools

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import NOT_QUOTE, SIGMA
from indic_text_normalization.core.utils import data_path, load_labels
from indic_text_normalization.te.constants import LANG, POINT_WORD, TE_CONSONANT

ONE = "ఒకటి"
OKA = "ఒక"

# Marker placed between a noun and a written case suffix before sandhi is applied.
SUFFIX_MARK = ""

# Telugu vowel signs U+0C3E TELUGU VOWEL SIGN AA .. U+0C4C TELUGU VOWEL SIGN AU.
VOWEL_SIGN = pynini.union(*[chr(i) for i in range(0x0C3E, 0x0C4D)]).optimize()

# Plural scale words and their singular counting form (ఐదు లక్షలు, ఒక లక్ష).
QUANTITY_SINGULAR = [
    ("వందలు", "వంద"),
    ("వందల", "వంద"),
    ("వేలు", "వెయ్యి"),
    ("వేల", "వెయ్యి"),
    ("లక్షలు", "లక్ష"),
    ("లక్షల", "లక్ష"),
    ("లక్షం", "లక్ష"),
    ("కోట్లు", "కోటి"),
    ("కోట్ల", "కోటి"),
    ("మిలియన్లు", "మిలియన్"),
    ("బిలియన్లు", "బిలియన్"),
    ("ట్రిలియన్లు", "ట్రిలియన్"),
]

NOT_ONE = pynini.difference(pynini.closure(NOT_QUOTE, 1), pynini.accep(ONE)).optimize()
ONE_AS_OKA = pynini.cross(ONE, OKA)

# ఒకటి heading a scale phrase (ఒకటి కోటి) reads as ఒక, but not before a decimal point
# (ఒకటి దశాంశం ఐదు కోట్లు keeps ఒకటి).
_NOT_POINT = pynini.difference(
    pynini.closure(NOT_QUOTE, 1), pynini.accep(POINT_WORD) + pynini.closure(NOT_QUOTE)
).optimize()
_ONE_PHRASE = (pynini.accep(ONE) + " " + _NOT_POINT).optimize()
ONE_PHRASE_AS_OKA = pynini.cross(ONE, OKA) + " " + _NOT_POINT
# Every amount other than a bare ఒకటి: a leading ఒకటి before a scale word becomes ఒక.
_OKA_SINGULAR = pynini.cdrewrite(
    pynini.string_map(QUANTITY_SINGULAR), OKA + " ", pynini.union(" ", "[EOS]"), SIGMA
)
MANY = (
    pynini.union(
        ONE_PHRASE_AS_OKA,
        pynini.difference(
            pynini.closure(NOT_QUOTE, 1), pynini.union(pynini.accep(ONE), _ONE_PHRASE).optimize()
        ),
    )
    @ _OKA_SINGULAR
).optimize()

# A plural scale word closing a number phrase takes its oblique -ల before the noun it
# counts: రెండు వేలు + రూపాయలు -> రెండు వేల రూపాయలు.
OBLIQUE_FINAL = pynini.cdrewrite(pynini.cross("లు", "ల"), "", "[EOS]", SIGMA).optimize()


def singularize_quantity(fst: pynini.Fst) -> pynini.Fst:
    """
    Map a plural scale word to its singular; leave any other word unchanged.
    """
    table = pynini.string_map(QUANTITY_SINGULAR).optimize()
    keys = pynini.project(table, "input").optimize()
    other = pynini.difference(pynini.closure(NOT_QUOTE, 1), keys)
    return (fst @ pynini.union(table, other)).optimize()


def _build_suffix_sandhi() -> pynini.Fst:
    """
    Build the sandhi rewrite chain; use ``suffix_sandhi``, which caches it.
    """
    mark = SUFFIX_MARK
    # -గా attaches to the nominative (రూపాయలుగా), so it takes no sandhi at all.
    nominative = pynini.cdrewrite(pynutil.delete(mark), "", pynini.union("గా", "గానే"), SIGMA)
    bare_la_right = pynini.accep("ల") + pynini.difference(
        pynini.union(TE_CONSONANT, " ", "[EOS]"), VOWEL_SIGN
    )
    drop_lu = pynini.cdrewrite(pynutil.delete("లు" + mark), "", bare_la_right, SIGMA)
    lu_to_la = pynini.cdrewrite(pynini.cross("లు" + mark, "ల"), "", "", SIGMA)
    anusvara = pynini.cdrewrite(
        pynini.union(
            pynini.cross("ం" + mark + "కి", "ానికి"),
            pynini.cross("ం" + mark + "కు", "ానికి"),
            pynini.cross("ం" + mark + "కే", "ానికే"),
            pynini.cross("ం" + mark + "ని", "ాన్ని"),
            pynini.cross("ం" + mark + "ను", "ాన్ని"),
            pynini.cross("ం" + mark + "కంటే", "ం కంటే"),
            pynini.cross("ం" + mark + "కన్నా", "ం కన్నా"),
            pynini.cross("ం" + mark + "నుండి", "ం నుండి"),
            pynini.cross("ం" + mark + "నుంచి", "ం నుంచి"),
            pynini.cross("ం" + mark + "వరకు", "ం వరకు"),
            pynini.cross("ం" + mark + "వరకూ", "ం వరకూ"),
            pynini.cross("ం" + mark + "దాకా", "ం దాకా"),
            pynini.cross("ం" + mark + "కోసం", "ం కోసం"),
        ),
        "",
        "",
        SIGMA,
    )
    vowel_suffix = pynini.cdrewrite(
        pynini.union(
            pynutil.delete("ు" + mark),
            pynutil.delete("ి" + mark),
            pynini.cross("ై" + mark, "య్య"),
        ),
        "",
        VOWEL_SIGN,
        SIGMA,
    )
    delete_mark = pynini.cdrewrite(pynutil.delete(mark), "", "", SIGMA)
    return (nominative @ drop_lu @ lu_to_la @ anusvara @ vowel_suffix @ delete_mark).optimize()


def optional_suffix_field() -> pynini.Fst:
    """
    Consume an optional ``suffix: "..."`` field, emitting the marked suffix text.
    """
    return pynini.closure(
        pynutil.delete(pynini.closure(" ", 0, 1))
        + pynutil.delete('suffix: "')
        + pynutil.insert(SUFFIX_MARK)
        + pynini.closure(NOT_QUOTE, 1)
        + pynutil.delete('"'),
        0,
        1,
    )


NBSP_TO_SPACE = pynini.cdrewrite(pynini.cross("\u00a0", " "), "", "", SIGMA).optimize()


def count_nouns() -> list[str]:
    """
    Nouns a numeral counts (numbers/count_nouns.tsv) plus the singular and plural unit words.
    """
    nouns = [row[0] for row in load_labels(data_path(LANG, "numbers/count_nouns.tsv"))]
    units = load_labels(data_path(LANG, "measure/unit.tsv"), min_fields=3)
    return nouns + [word for row in units for word in row[1:3]]


@functools.cache
def _suffix_sandhi_cached() -> pynini.Fst:
    return _build_suffix_sandhi()


def suffix_sandhi() -> pynini.Fst:
    """
    Join a noun and the case suffix after ``SUFFIX_MARK`` with regular Telugu sandhi.

    -లు + suffix -> -ల + suffix (రూపాయలు + కి -> రూపాయలకి); -లు + bare plural ల -> -ల
    (వేలు + లలో -> వేలలో); -ం + కి/కు/ని -> -ానికి/-ాన్ని (శాతం + కి -> శాతానికి);
    a vowel-sign suffix replaces a final -ు/-ి (ఐదు + ే -> ఐదే).
    """
    return _suffix_sandhi_cached().copy()
