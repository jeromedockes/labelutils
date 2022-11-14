"""Some tools eg Inception miscount characters outside the BMP.

This module provides conversions between indices in a unicode string and in a
utf-16 string (where surrogate pairs count as 2 characters).

"""
import numpy as np


class CharIndices:
    utf16_to_unicode: np.ndarray
    unicode_to_utf16: np.ndarray

    def __init__(self, text: str) -> None:
        # add an arbitrary byte at the end because one-past-the-end is a valid
        # index for end of position annotations so we need it in the conversion
        # table.
        utf_16 = np.frombuffer(
            (text.encode("utf-16-le") + b"\0x00"), dtype="<u2"
        )

        # an array containing 0 at the position of low surrogates and 1
        # elsewhere; summing counts unicode characters.
        # [0xDC00, 0xDFFF[ is the range of UTF16 low surrogates.
        non_trailing = np.ones(utf_16.shape, dtype="int8")
        non_trailing[(0xDC00 <= utf_16) & (utf_16 < 0xDFFF)] = 0

        # -1 because indices start at 0
        self.utf16_to_unicode = np.cumsum(non_trailing, dtype="int32") - 1

        # dropping low surrogates gives the positions of the start of each
        # unicode char.
        self.unicode_to_utf16 = np.arange(len(non_trailing), dtype="int32")[
            non_trailing.astype(bool)
        ]
