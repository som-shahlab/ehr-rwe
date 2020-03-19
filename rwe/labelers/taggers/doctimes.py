from rwe.labelers.taggers import *
from datetime import datetime

###############################################################################
#
# DocTime Tagger
#
###############################################################################

class DocTimeTagger(Tagger):

    def __init__(self, prop='doctime'):
        self.prop = prop

    def tag(self, document, **kwargs):
        if self.prop not in document.props:
            document.props['doctime'] = None
        elif type(document.props[self.prop]) is str:
            ts = datetime.strptime(document.props[self.prop], '%Y-%m-%d')
            document.props['doctime'] = ts

class TextFieldDocTimeTagger(Tagger):
    """
    Estimte document timestamp. Use either:
    1: Explicit note sign date of the form {field}:{datetime}, e.g.,
        T: 12-24-2005 11:30:00
    2: Most recent unambiguous TIMEX mention
    """

    def __init__(self, targets=None, field='T'):
        self.targets = targets if targets else ['TIMEX3', 'HEADER']
        self.field = field

    def tag(self, document, **kwargs):

        max_date, sign_dates = None, []
        for i in range(len(document.annotations)):
            header = document.annotations[i]['HEADER'][0] if 'HEADER' in document.annotations[i] else None
            timexs = document.annotations[i]['TIMEX3'] if 'TIMEX3' in document.annotations[i] else []
            ts = [ts.normalized for ts in timexs if ts.normalized]

            if ts:
                max_date = max([max_date] + ts) if max_date else max(ts)

            if ts and header and re.search("^\s*{}[:]".format(self.field), header.text):
                sign_dates.extend(ts)

        # defer to timestamps in the target field section
        if sign_dates:
            document.props['doctime'] = max(sign_dates)
        # select max from all datetimes
        elif max_date:
            document.props['doctime'] = max_date
        else:
            document.props['doctime'] = None


class MappedDocTimeTagger(Tagger):
    """
    Doctimes are provided in dictionary map of the form
        Dict[doc_name, datetime]
    """
    def __init__(self, doctimes):
        self.doctimes = doctimes

    def tag(self, document, **kwargs):
        document.props['doctime'] = self.doctimes[document.name] \
            if document.name in self.doctimes else None


