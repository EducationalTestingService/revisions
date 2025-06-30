"""
Utilities for (1) reading and writing pickles, 
(2) reading and writing JSON, (3) tokenizing, 
(4) applying a function to a DataFrame with multiprocessing.
"""

import gc
import json
import multiprocessing as mp
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from unicodedata import normalize

from nltk.tokenize import word_tokenize
from nltk.tokenize import sent_tokenize as sentence_tokenize

from tqdm import tqdm

tqdm.pandas()


_NON_ASCII = [
    ("\u2026", "..."),  # horizontal ellipsis
    ("\u201c", "``"),  # left double quotation mark
    ("\u201d", "''"),  # right double quotation mark
    ("\u2018", "`"),  # left single quotation mark
    ("\u2019", "'"),  # right single quotation mark
    ("\u2013", "-"),  # en dash
    ("\u00a0", " "),
]  # no-break space


class Config:
    def __init__(self, config_json):
        """
        Args:
            config_json (str): Path to the configuration JSON file.
        """
        with open(config_json) as infile:
            self.config = json.load(infile)

    def __getitem__(self, name):
        """
        Returns the full path.
        Args:
            name (str): Either a key in the configuration or
                a path that is relative to config["root"].
        """
        if name in self.config:
            return os.path.join(self.config["root"], self.config[name])
        else:
            path = os.path.join(self.config["root"], name)
            if (name in DIRS) and (not os.path.exists(path)):
                os.makedirs(path)
            return path


def unicode_normalize(unicode_text):
    for unicode_str, ascii_str in _NON_ASCII:
        unicode_text = unicode_text.replace(ascii_str, unicode_str)
    return normalize("NFKD", unicode_text)


def _apply_df(apply_arg_tuple):
    """
    Args:
        apply_arg_tuple (args):  3-tuple (group, func, kwargs)
            group (pd.DataFrame):   One group of a dataframe grouped by doc ID.
            func (function):        Function to apply to the dataframe.
            kwargs (dict):          Keyword arguments to func.
    """
    group, func, kwargs = apply_arg_tuple
    if "apply_to_row" in kwargs and kwargs["apply_to_row"]:
        group.progress_apply(lambda row: func(row, **kwargs), axis=1)
    else:
        func(group, **kwargs)


def multiprocessing_apply_df(groups, func, **kwargs):
    """
    Pass each chunk to `_apply_df` keeping all other arguments constant.

    Args:
        groups (pd.DataFrame):  Dataframe grouped along a dimension,
                                usually `meta_doc_id`.
        func (function):        Function to apply to the dataframe.
    """
    group_names, groups = zip(*groups)
    apply_args = [(d, func, kwargs) for d in groups]

    with ProcessPoolExecutor(max_workers=10) as executor:
        jobs = [executor.submit(_apply_df, a) for a in apply_args]
        results = []
        for job in tqdm(as_completed(jobs), total=len(jobs)):
            results.append(job.result())
    return results


def read_pickle(path):
    if not os.path.exists(path):
        return None
    gc.disable()
    with open(path, "rb") as handle:
        res = pickle.load(handle)
    gc.enable()
    return res


def write_pickle(path, obj):
    gc.disable()
    with open(path, "wb") as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)
    gc.enable()


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        return json.load(handle)


def write_json(path, obj):
    with open(path, "w") as handle:
        return json.dump(obj, handle, ensure_ascii=False, indent=2)


def tokenize_sentences(paragraphs):
    """
    Tokenize the sentences.
    Each empty newline is considered its own sentence.
    """
    sentences = []
    for par in paragraphs:
        if not par.strip():
            sentences.append(par)
        else:
            sentences.extend(sentence_tokenize(par))
    return sentences


def tokenize_text(text):
    """
    Args:
        text (str)
    Returns:
        Word-tokenized and sentence-tokenized string, joined on whitespace.
        Paragraphs are joined by newlines.
    """
    tokenized_pars = []
    for par in text.split("\n"):
        r = " ".join([" ".join(word_tokenize(s)) for s in sentence_tokenize(par)])
        tokenized_pars.append(r)
    return "\n".join(tokenized_pars)
