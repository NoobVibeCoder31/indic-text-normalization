"""
Path helper for Telugu data files.
"""

import os


def get_abs_path(rel_path: str) -> str:
    """
    Return the absolute path of a file relative to the ``te`` package directory.
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)
