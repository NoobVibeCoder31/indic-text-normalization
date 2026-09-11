"""
Malayalam spoken fraction shapes the shared ITN fraction tagger cannot derive.
"""

import pynini
from pynini.lib import pynutil

from indic_text_normalization.core.graph_utils import SIGMA, delete_space, insert_space
from indic_text_normalization.core.itn_taggers.cardinal import ItnCardinalFst

# The locative -ിൽ on the denominator, undone: നാലിൽ -> നാല്, ആയിരത്തിൽ -> ആയിരം, കോടിയിൽ -> കോടി.
DENOMINATOR_TO_NUMBER = (
    SIGMA
    + pynini.union(pynini.cross("ിൽ", "്"), pynini.cross("ത്തിൽ", "ം"), pynini.cross("ിയിൽ", "ി"))
).optimize()
# The conjunctive -ും on each part of a mixed number, undone: രണ്ടും -> രണ്ട്, ആയിരവും -> ആയിരം.
UM_TO_NUMBER = (
    SIGMA
    + pynini.union(pynini.cross("ും", "്"), pynini.cross("വും", "ം"), pynini.cross("ിയും", "ി"))
).optimize()


def mixed_number(cardinal: ItnCardinalFst) -> pynini.Fst:
    """
    രണ്ടും നാലിൽ മൂന്നും -> integer_part: "2" denominator: "4" numerator: "3".
    """
    with_um = (UM_TO_NUMBER @ cardinal.words_to_digits).optimize()
    denominator = (DENOMINATOR_TO_NUMBER @ cardinal.words_to_digits).optimize()
    return (
        pynutil.insert('integer_part: "')
        + with_um
        + pynutil.insert('"')
        + delete_space
        + insert_space
        + pynutil.insert('denominator: "')
        + denominator
        + pynutil.insert('"')
        + delete_space
        + insert_space
        + pynutil.insert('numerator: "')
        + with_um
        + pynutil.insert('"')
    ).optimize()
