import bz2
import codecs

def load_dict(filename, encoding="utf-8"):
    '''

    :param filename:
    :param encoding:
    :return:
    '''
    d = set()

    if filename.split(".")[-1] == "bz2":
        for line in bz2.BZ2File(filename, 'rb').readlines():
            line = line.strip()
            if len(line) == 0:
                continue
            d.add(line)
    else:
        with codecs.open(filename, "rU", encoding) as fp:
            for line in fp:
                line = line.strip()
                if len(line) == 0:
                    continue
                d.add(line)
    return d

def split_training_test_dev(filelists):
    rm = {'train':[], 'dev':[], 'test':[]}
    with open(filelists['dev'], 'rU') as dev_docs_fh:
        ddd = dev_docs_fh.read()
        for dd in ddd.splitlines():
            rm['dev'].append(dd)

    with open(filelists['train'], 'rU') as train_docs_fh:
        trdd = train_docs_fh.read()
        for trd in trdd.splitlines():
            rm['train'].append(trd)

    with open(filelists['test'], 'rU') as test_docs_fh:
        tedd = test_docs_fh.read()
        for ted in tedd.splitlines():
            rm['test'].append(ted)
    return rm

