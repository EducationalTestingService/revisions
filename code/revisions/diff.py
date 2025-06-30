"""
Detect diffs on the word level, based on
https://github.com/google/diff-match-patch/wiki/Line-or-Word-Diffs.

    `diff_wordsToChars`:    Copied directly from diff-match-patch.
    `diff_wordMode`:        Returns the token-level diff between two texts, 
                             along with the offsets in text1 and text2 
                             in a tuple (offsets1, offsets2).
"""

import copy

import diff_match_patch as dmp_module
from nltk.tokenize import word_tokenize
import spacy

nlp = spacy.load("en_core_web_sm")


def diff_wordsToChars(text1, text2):
    """
    This function is copied and modified from `diff_linestoChars`
    from the python3 diff-match-patch script.

    Split two texts into an array of strings.  Reduce the texts to a string
    of hashes where each Unicode character represents one word.

    Args:
      text1: First string.
      text2: Second string.
    Returns:
      Three element tuple, containing the encoded text1, the encoded text2 and
      the array of unique strings.  The zeroth element of the array of unique
      strings is intentionally blank.
    """
    lineArray = []  # e.g. lineArray[4] == "Hello\n"
    lineHash = {}  # e.g. lineHash["Hello\n"] == 4

    # "\x00" is a valid character, but various debuggers don't like it.
    # So we'll insert a junk entry to avoid generating a null character.
    lineArray.append("")

    def diff_linesToCharsMunge(text):
        """Split a text into an array of strings.  Reduce the texts to a string
        of hashes where each Unicode character represents one word.
        Modifies linearray and linehash through being a closure.
        Args:
            text: String to encode.
        Returns:
            Encoded string.
        """
        chars = []
        # Walk the text, pulling out a substring for each line.
        # text.split('\n') would would temporarily double our memory footprint.
        # Modifying text would create many large strings to garbage collect.
        lineStart = 0
        lineEnd = -1

        # Make sure the tokens are joined on whitespace, but keep newlines
        words = []
        offset_list = []
        for i, line in enumerate(text.split("\n")):
            if line.strip():
                word_tuples = [
                    (w.text, (w.idx, w.idx + len(w.text))) for w in nlp(line)
                ]

                if word_tuples:
                    line_words, offset_list = zip(*word_tuples)
                    words.extend(line_words)

        if text.endswith("\n"):
            # Get the full whitespace string
            words.append("\n")

        # I add a space at the end of the text (otherwise identical
        # words won't hash to the same character). The unintended
        # consequence is that the text returned in the diff will be
        # followed by an extra space.
        text = " ".join(words) + " "

        while lineEnd < len(text) - 1:
            lineEnd = text.find(" ", lineStart)  # Break on space instead of \n

            if lineEnd == -1:
                lineEnd = len(text) - 1
            line = text[lineStart : lineEnd + 1]

            if line in lineHash:
                char = chr(lineHash[line])
                chars.append(char)
            else:
                if len(lineArray) == maxLines:
                    # Bail out at 1114111 because chr(1114112) throws.
                    line = text[lineStart:]
                    lineEnd = len(text)
                lineArray.append(line)
                lineHash[line] = len(lineArray) - 1
                char = chr(len(lineArray) - 1)
                chars.append(char)
            lineStart = lineEnd + 1
        return "".join(chars), offset_list

    # Allocate 2/3rds of the space for text1, the rest for text2.
    maxLines = 666666
    chars1, offsets1 = diff_linesToCharsMunge(text1)
    maxLines = 1114111
    chars2, offsets2 = diff_linesToCharsMunge(text2)
    return (chars1, chars2, lineArray, (offsets1, offsets2))


def diff_wordMode(text1, text2, return_offsets=True):
    dmp = dmp_module.diff_match_patch()
    a = diff_wordsToChars(text1, text2)
    lineText1, lineText2, lineArray, offsets = a
    diff = dmp.diff_main(lineText1, lineText2)
    char_diff = copy.deepcopy(diff)
    dmp.diff_charsToLines(diff, lineArray)

    if return_offsets:
        return diff, char_diff, offsets
    return diff
