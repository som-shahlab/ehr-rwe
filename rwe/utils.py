import re
import bz2
import os
import glob
import random
import itertools
import numpy as np
import pandas as pd
from rwe.contexts import Document, Span, Relation
from typing import List, Set, Dict, Tuple, Optional, Union, Iterable
from .dataloaders import dataloader

###############################################################################
#
# Misc Tools
#
###############################################################################

def load_dict(fpath: str,
              stopwords: Set[str] = None,
              ignore_case: bool = False) -> Set[str]:
    """Load dictionary of terms/concepts

    Parameters
    ----------
    fpath
    stopwords
    ignore_case

    Returns
    -------

    """
    stopwords = {} if not stopwords else stopwords
    ext = fpath.split(".")[-1]
    fp = bz2.BZ2File(fpath,'r') if ext == 'bz2' else open(fpath,'r')

    d = set()
    for line in fp:
        line = line.strip()
        t = line.decode('utf-8') if type(line) is bytes else line
        t = t.lower() if ignore_case else t
        if t in stopwords or not t.strip():
            continue
        d.add(t)
    return d

def build_candidate_set(documents: List[Document],
                        target: str) -> List[Union[Span, Relation]]:
    """

    Parameters
    ----------
    documents
    target

    Returns
    -------

    """
    Xs = []
    for doc in documents:
        xs = [doc.annotations[i][target] for i in doc.annotations
              if target in doc.annotations[i]]
        Xs.extend(itertools.chain.from_iterable(xs))
    return Xs


def parse_stable_label(s):
    """Parse old Snorkel stable label format."""
    spans = []
    doc_name = None
    for arg in s.split('~~'):
        fields = arg.split(":")
        doc_name = fields[0]
        spans.append((int(fields[-2]), int(fields[-1])))
    return (doc_name, spans)


def get_parent_sentence(doc, char_start, char_end):
    offsets = [s.abs_char_offsets[0] for s in doc.sentences]
    for i in range(len(offsets) - 1):
        if char_start >= offsets[i] and char_end <= offsets[i + 1]:
            return doc.sentences[i]
    return doc.sentences[i + 1]


def load_gold(fpath, documents, type_def):
    """ Load Snorkel v0.7 gold label set"""
    doc_idx = {doc.name: doc for doc in documents}
    type_name, arg_names = type_def

    candidates = {}
    df = pd.read_csv(fpath, sep="\t")
    for i, row in df.iterrows():
        cand = parse_stable_label(row['context_stable_ids'])
        label = int(row['label'])
        label = 0 if label == -1 else label

        doc = doc_idx[cand[0]]
        spans = []
        for span in cand[-1]:
            start, end = span
            sent = get_parent_sentence(doc, *span)
            offset = sent.abs_char_offsets[0]
            spans.append(Span(start - offset, end - offset, sent))

        args = dict(zip(arg_names, spans))
        rela = Relation(type_name, args)
        candidates[rela] = label
    return candidates


###############################################################################
#
# Sampling
#
###############################################################################

def reservoir_sampling(iterable: Iterable,
                       n: int,
                       seed: int = 1234):
    """
    Standard reservoir sampling of a Python iterable.
    """
    np.random.seed(seed)
    i = 0
    pool = []
    for item in iterable:
        if len(pool) < n:
            pool.append(item)
        else:
            i += 1
            k = random.randint(0, i)
            if k < n:
                pool[k] = item
    return pool


def load_unlabeled_sample(fpath: str,
                          num_samples: int ,
                          seed: int = 1234,
                          max_docs: int = 100000):
    """
    Reservoir sample JSON documents. If `seed` and `max_docs` are fixed,
    then this returns a deterministic subsample of the docs at `fpath`.
    """
    filelist = glob.glob(f"{fpath}/*") if os.path.isdir(fpath) else [fpath]
    assert len(filelist) > 0

    sample = reservoir_sampling(dataloader(filelist), max_docs, seed)
    return sample[0:num_samples]


###############################################################################
#
# DEPRICATED
#
###############################################################################
# from rwe.labelers.taggers import *
#
# # build label set
# n_samples = 1000
# samples = []
# sample_docs = {}
# for doc in documents[0]:
#     if len(samples) > n_samples:
#         break
#     for i in doc.annotations:
#         if 'pain-at' in doc.annotations[i]:
#             sample_docs[doc.name] = 1
#             samples.extend(doc.annotations[i]['pain-at'])
#
# annotations = []
# for c in samples:
#     head, tail = (
#     c.pain, c.anatomy) if c.pain.char_start < c.anatomy.char_start else (
#     c.anatomy, c.pain)
#     left = get_left_span(head)
#     btw = get_between_span(head, tail)
#     right = get_right_span(tail)
#
#     left = [w for w in left.get_attrib_tokens('words') if
#             w.strip()] if left else []
#     btw = [w for w in btw.get_attrib_tokens('words') if
#            w.strip()] if btw else []
#     right = [w for w in right.get_attrib_tokens('words') if
#              w.strip()] if right else []
#
#     head = [w for w in head.get_attrib_tokens('words') if w.strip()]
#     tail = [w for w in tail.get_attrib_tokens('words') if w.strip()]
#
#     row = [' '.join(left), ' '.join(head), ' '.join(btw), ' '.join(tail),
#            ' '.join(right)]
#     annotations.append(row)
#
# with open('/users/fries/desktop/mimic_pain-at_gold.tsv', 'w') as fp:
#     fp.write('\t'.join(['LEFT', 'HEAD', 'BTW', 'TAIL', 'RIGHT']) + '\n')
#     for row in annotations:
#         fp.write('\t'.join(row) + '\n')