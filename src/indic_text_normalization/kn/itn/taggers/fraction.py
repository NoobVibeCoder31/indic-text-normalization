"""
Kannada spoken fraction shapes for the shared ITN fraction tagger.
"""

import pynini

from indic_text_normalization.core.graph_utils import SIGMA

# The locative -ರಲ್ಲಿ on the denominator, undone: ನಾಲ್ಕರಲ್ಲಿ -> ನಾಲ್ಕು, ಸಾವಿರದಲ್ಲಿ -> ಸಾವಿರ,
# ಕೋಟಿಯಲ್ಲಿ -> ಕೋಟಿ.
DENOMINATOR_TO_NUMBER = (
    SIGMA
    + pynini.union(pynini.cross("ರಲ್ಲಿ", "ು"), pynini.cross("ದಲ್ಲಿ", ""), pynini.cross("ಯಲ್ಲಿ", ""))
).optimize()
