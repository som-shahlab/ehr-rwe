import re
import csv
from collections import defaultdict
from ..helpers import get_left_span, get_right_span

class NegEx(object):
    '''
    Negex

    Chapman, Wendy W., et al. "A simple algorithm for identifying negated findings and
    diseases in discharge summaries." Journal of biomedical informatics 34.5 (2001): 301-310.
    '''
    def __init__(self,data_root='supervision/dicts/negex'):
        self.data_root = data_root
        self.filename = "negex_multilingual_lexicon-en-de-fr-sv.csv"
        self.dictionary = NegEx.load("{}/{}".format(self.data_root, self.filename))
        self.rgxs = NegEx.build_regexs(self.dictionary)

    def negation(self, span, category, direction, window=3):
        """
        Return any matched negex phrases

        :param span:
        :param category:
        :param direction:
        :param window:
        :return:
        """
        rgx = self.rgxs[category][direction]
        if not rgx.pattern:
            return None

        cxt = get_left_span(span, window=window) if direction == 'left' \
            else get_right_span(span, window=window)

        m = rgx.findall(cxt.text)
        return m if m else None

    def is_negated(self, span, category, direction, window=3):
        """
        Boolean test for negated spans

        :param span:
        :param category:
        :param direction:
        :param window:
        :return:
        """
        rgx = self.rgxs[category][direction]
        if not rgx.pattern:
            return False

        negation_match = self.negation(span, category, direction, window)
        return True if negation_match else False

    def all_negations(self, span, window=3):

        ntypes = []
        for category in self.rgxs:
            for direction in self.rgxs[category]:
                m = self.negation(span, category, direction, window)
                if m:
                    ntypes.append((category, direction, m))

        return ntypes


    @staticmethod
    def build_regexs(dictionary):
        """

        :param dictionary:
        :return:
        """
        rgxs = defaultdict(dict)
        for category in dictionary:
            fwd = [t["term"] for t in dictionary[category] if t['direction'] in ['forward', 'bidirectional']]
            bwd = [t["term"] for t in dictionary[category] if t['direction'] in ['backward', 'bidirectional']]
            rgxs[category]['left'] = "|".join(sorted(fwd, key=len, reverse=1))
            rgxs[category]['right'] = "|".join(sorted(bwd, key=len, reverse=1))

            if not rgxs[category]['left']:
                del rgxs[category]['left']
            if not rgxs[category]['right']:
                del rgxs[category]['right']
            for direction in rgxs[category]:
                p = rgxs[category][direction]
                rgxs[category][direction] = re.compile(r"({})(\b|$)".format(p), flags=re.I)

        return rgxs


    @staticmethod
    def load(filename):
        '''
        Load negex definitions
        :param filename:
        :return:
        '''
        negex = defaultdict(list)
        with open(filename, 'rU') as of:
            reader = csv.reader(of, delimiter=',')
            for row in reader:
                term = row[0]
                category = row[30]
                direction = row[32]
                if category == 'definiteNegatedExistence':
                    negex['definite'].append({'term': term, 'direction': direction})
                elif category == 'probableNegatedExistence':
                    negex['probable'].append({'term': term, 'direction': direction})
                elif category == 'pseudoNegation':
                    negex['pseudo'].append({'term': term, 'direction': direction})
        return negex


