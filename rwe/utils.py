import re
import bz2
import itertools
import pandas as pd
from rwe.contexts import Document, Span, Relation
from typing import List, Set, Dict, Tuple, Optional, Union

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

