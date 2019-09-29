import re
import sys
import glob
import json
import time
import logging
import argparse
import pandas as pd
from pathlib import Path
from joblib import Parallel, delayed
from functools import partial
from spacy.util import minibatch
from pipes.tokenizers import get_parser, parse_doc

logger = logging.getLogger(__name__)


def timeit(f):
    """
    Decorator for timing function calls
    :param f:
    :return:
    """
    def timed(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logger.info(f'{f.__name__} took: {te - ts:2.4f} sec')
        return result

    return timed

def mimic_doc_preprocessor(s):
    """Replace MIMIC-III anonymization tags of the form
        [**First Name8 (NamePattern2)**] with
        |||First_Name8_(NamePattern2)|||
    This results in fewer tokenization and SBD errors.

    Parameters
    ----------
    s

    Returns
    -------

    """
    rgx = r'''(\[\*\*)[a-zA-Z0-9_/()\- ]+?(\*\*\])'''
    for m in re.finditer(rgx, s):
        repl = m.group().replace('[**', '|||').replace('**]', '|||')
        repl = re.sub("[/()]", "|", repl)
        s = s.replace(m.group(), repl.replace(" ", "_"))

    m = re.search(r'''[?]{3,}''', s)
    if m:
        s = s.replace(m.group(), u"•" * (len(m.group())))
    return s

def transform_texts(nlp, batch_id, corpus, output_dir, disable=[], prefix=''):
    """

    :param nlp:
    :param batch_id:
    :param corpus:
    :param output_dir:
    :param disable:
    :param prefix:
    :return:
    """
    out_path = Path(output_dir) / (
        f"{prefix + '.' if prefix else ''}{batch_id}.json")
    print("Processing batch", batch_id)

    with out_path.open("w", encoding="utf8") as f:
        doc_names, texts = zip(*corpus)
        for i, doc in enumerate(nlp.pipe(texts)):
            sents = list(parse_doc(doc, disable=disable))
            f.write(
                json.dumps({'name': str(doc_names[i]), 'sentences': sents}))
            f.write("\n")
    print("Saved {} texts to JSON {}".format(len(texts), batch_id))


def dataloader(inputdir, preprocess=lambda x: x):
    """

    :param inputdir:
    :param preprocess:
    :return:
    """
    filelist = glob.glob(inputdir + "/*.tsv")
    for fpath in filelist:
        print(fpath)
        df = pd.read_csv(fpath, delimiter='\t', header=0, quotechar='"')  #
        for i, row in df.iterrows():
            doc_name = row['DOC_NAME']
            text = row['TEXT'].replace('\\n', '\n').replace('\\t', '\t')
            if not text.strip():
                logger.error(
                    f"Document {doc_name} contains no text -- skipping")
                continue
            yield (doc_name, preprocess(text))


@timeit
def main(args):
    nlp = get_parser(disable=args.disable.split(','))
    
    identity_preprocess = lambda x:x
    corpus = dataloader(args.inputdir, preprocess=mimic_doc_preprocessor)

    partitions = minibatch(corpus, size=args.batch_size)
    executor = Parallel(n_jobs=args.n_procs,
                        backend="multiprocessing",
                        prefer="processes")
    do = delayed(partial(transform_texts, nlp))
    tasks = (do(i, batch, args.outputdir, args.disable, args.prefix) for
             i, batch in enumerate(partitions))
    executor(tasks)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-i", "--inputdir", type=str, default=None,
                           help="input directory")
    argparser.add_argument("-o", "--outputdir", type=str, default=None,
                           help="output directory")
    argparser.add_argument("-F", "--fmt", type=str, default="single",
                           help="document format (single|row)")
    argparser.add_argument("-p", "--prefix", type=str, default="",
                           help="json name prefix")
    argparser.add_argument("-n", "--n_procs", type=int, default=2,
                           help="number of processes")
    argparser.add_argument("-b", "--batch_size", type=int, default=1000,
                           help="batch size")
    argparser.add_argument("-d", "--disable", type=str,
                           default="ner,parser,tagger",
                           help="disable spaCy components")

    argparser.add_argument("--quiet", action='store_true',
                           help="supress logging")
    args = argparser.parse_args()

    if not args.quiet:
        FORMAT = '%(message)s'
        logging.basicConfig(format=FORMAT, stream=sys.stdout,
                            level=logging.INFO)

    logger.info(f'Python:      {sys.version}')
    for attrib in args.__dict__.keys():
        v = 'None' if not args.__dict__[attrib] else args.__dict__[attrib]
        logger.info("{:<15}: {:<10}".format(attrib, v))

    main(args)
