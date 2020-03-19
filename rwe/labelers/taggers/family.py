import datetime
from rwe.helpers import *
from rwe.labelers.taggers import *
from functools import partial
#from scipy.stats import mode
from statistics import mode
import numpy as np

#################################################################################
#
# Family (Subject) Tagger
#
#################################################################################

PATIENT = 1
OTHER   = 2
ABSTAIN = 0

rgx_relatives = re.compile(r'''\b(((grand)*(mother|father)|grand(m|p)a)([']*s)*|((parent|(daught|sist|broth)er|son|cousin)([']*s)*))\b''', re.I)

def LF_relative(span):
    text = get_left_span(span, span.sentence, window=6).text
    return OTHER if rgx_relatives.search(text) else PATIENT

def LF_ext_family(span):
    rgx = re.compile(r'''\b(spouse|wife|husband)\b''', re.I)
    text = get_left_span(span, span.sentence, window=6).text
    return OTHER if rgx.search(text) else ABSTAIN

def LF_social(span):
    rgx = re.compile(r'''\b(friend(s)*|roomate(s)*|passanger(s)*)\b''', re.I)
    text = get_left_span(span, span.sentence, window=6).text
    return OTHER if rgx.search(text) else ABSTAIN

def LF_header(span):
    rgx = re.compile(r'''(family history[:]|family hx)\b''', re.I)
    return OTHER if rgx.search(span.sentence.text.strip()) else ABSTAIN

def LF_history_of(span):
    rgx = r'''\bfamily (history of|hx)'''
    text = get_left_span(span, span.sentence, window=6).text
    return OTHER if re.search(rgx, text.strip(), re.I) else ABSTAIN

def LF_donor(span):
    rgx = r'''\b(donor)\b'''
    text = get_left_span(span, span.sentence, window=6).text
    return OTHER if re.search(rgx, span.sentence.text.strip(), re.I) else ABSTAIN


class FamilyTagger(Tagger):
    """
    Concepts are generally attached to the patient. However, there are cases
    where concepts attach to family members or donors.

    """

    def __init__(self, targets, label_reduction='or'):
        self.prop_name = 'subject'
        self.targets = targets
        self.label_reduction = label_reduction

        self.lfs = [
            LF_relative,
            LF_ext_family,
            LF_social,
            LF_header,
            LF_history_of,
            LF_donor
        ]

        self.class_map = {
            1: "patient",
            2: "family/other"
        }

    def _apply_lfs(self, span):
        """ Apply labeling functions. """
        return np.array([lf(span) for lf in self.lfs])

    def tag(self, document, **kwargs):
        for i in document.annotations:
            # apply to the following concept targets
            for layer in self.targets:
                if layer not in document.annotations[i]:
                    continue
                for span in document.annotations[i][layer]:
                    L = self._apply_lfs(span)
                    # majority vote
                    if L.any() and self.label_reduction == 'mv':
                        try:
                            y = mode(L[L.nonzero()])
                        except:
                            # break ties
                            y = 2
                        span.props[self.prop_name] = y

                    # logical or
                    elif L.any() and self.label_reduction == 'or':
                        if 2 in L:
                            span.props[self.prop_name] = self.class_map[2]
                        else:
                            span.props[self.prop_name] = self.class_map[1]
