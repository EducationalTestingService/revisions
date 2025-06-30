"""
# Revisions

Revisions is a tool that finds the differences between two texts and then outputs a JSON file with the changes and their character indices, along with an HTML file displaying the changes. While there are several tools that accomplish this, few show reliable changes (insertions, deletions, and substitutions) at the word level for long texts. This package utilizes [MassAlign](https://github.com/ghpaetzold/massalign) to link paragraphs and sentences, and then [diff-match-patch](https://github.com/google/diff-match-patch) to find changes at the word-level.


## I. Configuration file

A sample configuration file `sample_config.json` is provided.

What the fields mean:

* `root` is the path to the cloned repository. **This must be changed.**
* `stop_words` is the path to a text file with one stop word on each line. A default is provided in the repository.

Make a copy of `sample_config.json` and make changes as needed. After this point, the documentation assumes that your copy of the configuration file is called `config.json`.

## II. Getting revisions
Note: the scripts assume *utf-8 encoding* (the default in Python 3).
All text is run through `revisions.utils.unicode_normalize` to remove ASCII characters and normalize unicode characters. 

Given two documents, the script will produce an HTML file and a JSON file. \
   The HTML displays the document versions side by side with the revisions highlighted, while the JSON contains revision offsets.


### Compare two document versions
Given two text files where the text of version n is in `file1` and the text of version n+1 is in `file2`, produce the output files.

```
python3 code/revisions/get_single_output.py --help
```

### Parsing the JSON file

Printing the aligned sentences and their revisions:

```python
import json

with open(path/to/json) as infile:
   edits_json = json.load(infile)

for s1_index, alignment_dict in edits_json["alignments"]:
   s1 = edits_json["file1_sentences"][s1_index]["text"]
   s2 = [edits_json["file2_sentences"][s2_index] for s2_index in alignment_dict["match"]]

   print(s1)
   print(s2)
   print(alignment_dict["edits"])
   print("")
```

## IV. Tests
```
cd code/revisions/tests
pytest
```
"""


from .aligned_text import AlignedText
from .diff import diff_wordMode
from .edits_html import EditsHtml
from .utils import Config
