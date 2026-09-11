"""
Hindi number-word helpers shared by the TN verbalizers.
"""

import pynini

from indic_text_normalization.core.graph_utils import NOT_QUOTE, SIGMA

ONE = "एक"
NOT_ONE = pynini.difference(pynini.closure(NOT_QUOTE, 1), pynini.accep(ONE)).optimize()
NBSP_TO_SPACE = pynini.cdrewrite(pynini.cross(" ", " "), "", "", SIGMA).optimize()
