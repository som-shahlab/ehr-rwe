import re
from collections import defaultdict
from rwe.helpers import *
from rwe.labelers.taggers import *

###############################################################################
#
# Section Header Taggers
#
###############################################################################

class SectionHeaderTagger(Tagger):
    """
    Identify possible section headers such as:
        HPI:
        HOSPITAL COURSE:
    """
    def __init__(self, max_token_len=6):
        self.max_token_len = max_token_len
        self._init()

    def _init(self):
        """Regular expression for detecting section headers."""
        rgx = '(?:^[\s\n]*|[\n])((?:(?:[A-Za-z#.,]+|24hrs)\s{0,1}){1,' + \
              str(self.max_token_len) + '}[:])'
        self.matchers = {"HEADER": re.compile(rgx, re.I)}

    def _matches(self, rgx, doc, ngrams, group=0):
        """
        For each sentence, return all matches for the provided regex pattern.
        """
        text = ''
        for i, sent in enumerate(doc.sentences):
            for match in rgx.finditer(sent.text):
                span = match.span(group)
                start, end = span
                # remove trailing colon
                if match.group()[-1] == ':':
                    end -= 1
                tspan = Span(char_start=start, char_end=end - 1, sentence=sent)
                yield (i, tspan)

    def tag(self, document, ngrams=6, stopwords=[]):
        """ """
        candgen = Ngrams(n_max=ngrams)
        matches = defaultdict(list)
        for sidx, match in self._matches(self.matchers["HEADER"],
                                         document,
                                         candgen,
                                         group=1):
            # ignore stopwords
            if match.get_span().lower() in stopwords:
                continue
            matches[sidx].append(match)

        # build header indices for all sentences
        # this captures what section header a sentence lives under
        curr = [None]
        header_index = {}
        for j in range(len(document.sentences)):
            if j in matches:
                curr = matches[j]
            header_index[j] = curr

        for sidx in header_index:
            document.annotations[sidx].update({'HEADER': header_index[sidx]})


class ParentSectionTagger(Tagger):

    def __init__(self, targets):
        self.prop_name = 'section'
        self.targets = targets

    def tag(self, document, **kwargs):
        for i in document.annotations:
            for layer in self.targets:
                if layer not in document.annotations[i]:
                    continue
                for span in document.annotations[i][layer]:
                    annos = span.sentence.document.annotations
                    header = annos[span.sentence.i]['HEADER'][-1]
                    span.props[self.prop_name] = header