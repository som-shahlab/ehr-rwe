from .relation import *
from ..negex import *
from ..utils import load_dict

class PainLocationRelation(LabelingFuncGen):

    def __init__(self, candidates):
        """

        :param candidates:
        """
        super(PainLocationRelation, self).__init__('pain-intensity')
        self.candidates
        self._init_deps()


    def _init_deps(self):

        negex = NegEx("../data/dicts/negex")

        # see 'Qualitative Concept', 'Finding', 'Sign or Symptom'
        dict_intensity = set(['sharp', 'intense', 'extreme', 'worsening', 'moderate', 'minimal', 'moderate',
                              'mild', 'significant', 'crushing', 'severe', 'excruciating', 'slight',
                              'unbearable'])

        # Pain scores
        rgx = "pain\s*(score|level)*\s*[:]*\s*[~]*[0-9][.+-]*[0-9]*[/][0-9]+"

        self.lfs = []