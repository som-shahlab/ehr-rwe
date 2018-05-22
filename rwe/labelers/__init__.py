import rwe
from rwe.labelers.lfs import *
from rwe.utils import load_dict
from rwe.labelers.negex import *

dict_pain = load_dict("../data/supervision/dicts/nociception/nociception.curated.txt")
dict_anatomy = load_dict("../data/supervision/dicts/anatomy/fma_human_anatomy.bz2")

negex = NegEx("../data/supervision/dicts/negex")

def get_labeling_functions(setname):

    if setname == "pain_anatomy":
        lfs = [rwe.labelers.__dict__.get(lf) for lf in dir(rwe.labelers)]
        return [lf for lf in lfs if callable(lf) and lf.__name__[0:3] == "LF_"]
    else:
        return []