"""
The spoken Malayalam clock vocabulary the shared ITN time tagger reads.
"""

from indic_text_normalization.core.itn_taggers.time import ItnTimeWords

ITN_TIME_WORDS = ItnTimeWords(
    hour_nouns=("മണി",),
    minute_nouns=("മിനിറ്റ്", "മിനിട്ട്", "മിനുട്ട്", "മിനിറ്റുകൾ"),
    second_nouns=("സെക്കൻഡ്", "സെക്കന്റ്", "സെക്കൻറ്", "സെക്കൻഡുകൾ"),
    hour_suffixed=(("മണിക്ക്", "ന്"), ("മണിയോടെ", "ഓടെ"), ("മണിയായി", "ആയി")),
    minute_suffixed=(("മിനിറ്റിന്", "ന്"), ("മിനിറ്റോടെ", "ഓടെ")),
    second_suffixed=(("സെക്കൻഡിന്", "ന്"),),
    hour_one=("ഒരു", "മണി"),
    minute_one="ഒരു",
    half_glued_suffixes=(("യ്ക്ക്", "ന്"), ("യോടെ", "ഓടെ")),
)
