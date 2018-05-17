'''


'''
import os
import re
import glob
import codecs
#import shutil
import numpy as np

np.random.seed(123456)

# ----------------------------------------------------------------------
#
#  CLEF Corpus Preprocessing Functions
#
# ----------------------------------------------------------------------

class ClefCorpus(object):

    def __init__(self, inputdir, cachedir="cache", encoding="latin2"):
        self.encoding = encoding
        self.filelist = glob.glob(inputdir + "*")
        np.random.shuffle(self.filelist)

        outdir = "/".join(inputdir.rstrip("/").split("/")[:-1])
        self.cachedir = "{}/{}".format(outdir,cachedir)
        if not os.path.exists(self.cachedir):
            os.makedirs(self.cachedir)
            print "Created directory {}".format(self.cachedir)

        print len(self.filelist)
        # preprocess document (e.g., peform cleanup and other tasks)
        for fn in self.filelist:
            outfile = "{}/{}".format(self.cachedir,fn.split("/")[-1])
            txt = self._preprocess_doc(fn)
            with codecs.open(outfile, "w", "latin2") as fp:
                fp.write(txt)

        self.fold_idx = self._init_folds()

    def _init_folds(self):

        self.filelist = glob.glob(self.cachedir + "/*.txt")
        self.folds = {}
        #self.folds["train"] = self.filelist[0:150]
        #self.folds["dev"]   = self.filelist[150:200]
        #self.folds["test"]  = self.filelist[200:]

        self.folds["train"] = self.filelist[150:200]
        self.folds["dev"] = self.filelist[200:]
        self.folds["test"] = self.filelist[0:150]


        #Candidates(Train):   137
        #Candidates(Dev):     240
        #Candidates(Test):    73

        self.folds["train"] = [os.path.basename(fn).split(".")[0] + "::document:0:0" for fn in self.folds["train"]]
        self.folds["dev"] = [os.path.basename(fn).split(".")[0] + "::document:0:0" for fn in self.folds["dev"]]
        self.folds["test"] = [os.path.basename(fn).split(".")[0] + "::document:0:0" for fn in self.folds["test"]]

        fold_idx = {doc_id: "train" for doc_id in self.folds['train']}
        fold_idx.update({doc_id: "dev" for doc_id in self.folds['dev']})
        fold_idx.update({doc_id: "test" for doc_id in self.folds['test']})

        return fold_idx

    def _preprocess_doc(self, infile, normalize=False):
        '''CLEF-specific cleanup to assist in better parsing'''
        txt = ""
        with codecs.open(infile ,"rU" ,self.encoding) as fp:
            lines = fp.readlines()

            if normalize:
                lines = [l for l in lines if "||||" not in l] # remove semi-structured components
                lines = [re.sub(r"([A-Za-z]{3,})([/])([A-Za-z]{3,})", r"\1 \2 \3", l) for l in lines] # fix / splits
                txt ,fields = self._unblind("".join(lines))
                for tag in fields:
                    rpl = fields[tag]
                    rpl = re.sub("[() ]" ,"" ,rpl)
                    rpl = rpl.replace("[**" ,"").replace("**]" ,"")
                    txt = txt.replace(tag ,rpl)

            txt = "".join(lines)
        return txt


    def _unblind(self, txt):
        # find all protected health info spans
        fields = re.findall('(\[[*]{2,2}.+?[*]{2,2}\])', txt, re.DOTALL)
        fields = {str(abs(hash(s)) % (10 ** 16)): s for s in fields}
        for rpl, tag in fields.items():
            txt = txt.replace(tag, rpl)
        return txt, fields



# def train_dev_test_split(outdir):
#     np.random.shuffle(filelist)
#     written = {}
#
#     train = filelist[0:150]
#     dev  = filelist[150:200]
#     test = filelist[200:]
#
#     # create subdirectories for random folds
#     splits = {"train":train,"dev":dev,"test":test}
#     for setname in splits:
#         dirname = outdir + "/" + setname + "/"
#         print dirname
#         if not os.path.exists(dirname):
#             os.mkdir(dirname)
#
#         for fname in splits[setname]:
#             if fname.split("/")[-1] in written:
#                 continue
#             outfile = outdir + setname + "/" + fname.split("/")[-1]
#             process_clef_document(fname,outfile)
#             written[fname.split("/")[-1]] = 1