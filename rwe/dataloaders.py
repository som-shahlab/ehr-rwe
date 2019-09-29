import glob
import gzip
import json
from .contexts import Document, Sentence
from typing import Tuple, List, Dict

def parse_doc(d) -> Document:
    """Convert JSON into container objects. Most time is spent loading JSON.
    Transforming to Document/Sentence objects comes at ~13% overhead.

    Parameters
    ----------
    d
        dictionary of document kwargs

    Returns
    -------

    """
    sents = [Sentence(**s) for s in d['sentences']]
    return Document(d['name'], sents)

def dataloader(filelist: List[str]) -> List[Document]:
    """Load compressed JSON files

    Parameters
    ----------
    filelist

    Returns
    -------

    """
    documents = []
    for fpath in filelist:
        fopen = gzip.open if fpath.split(".")[-1] == 'gz' else open
        with fopen(fpath,'rb') as fp:
            for line in fp:
                doc = parse_doc(json.loads(line))
                documents.append(doc)
    return documents
