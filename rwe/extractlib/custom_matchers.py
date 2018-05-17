import bz2
import glob
import codecs
from rwe.extractlib.utils import *
from snorkel.matchers import *

class AnatomicalSiteMatcher(Union):

    def __init__(self, dictionary, longest_match_only=True):
        self.dictionary = dictionary
        self.longest_match_only = longest_match_only
        self.children = self._init_matchers()


    def _init_matchers(self):
        """


        TODO: 5/22 Add matchers for
            extensor hallucis longus tendon sheath
            anterior tibialis tendon
            right greater trochanter
            right SI joint

            Myofascial

        add new pain sensation:

            dysesthesia
            crepitus  - "a grating sound or sensation produced by friction between bone and cartilage or the fractured parts of a bone."

        :return:
        """

        # create anatomy dictionary matcher
        stopwords = set(["blood", "x", "s", "p", 'pt', 'capsule', 'cm', 'mm','r','incision','md'])
        anatomy_dict = {t:1 for t in self.dictionary if t.lower() not in stopwords and len(t) > 1}
        # custom anatomical terms
        anatomy_terms = ['LUE','RUE','(R)hip','(L)hip','lue','rue', 'sternal', 'LE', 'le',
                         'ischial', 'joint compartments', 'joint compartment',
                         '(r)hip','(l)hip', '(r)knee','(l)knee', '(r)hand','(l)hand',
                         '(r)leg', '(l)leg', '(r)extremity','(l)extremity' ]
        for t in anatomy_terms:
            anatomy_dict[t] = 1

        # manual dictionary terms
        terms = dict.fromkeys(["abd", "abdominal", "costovertebral", 'shoulder blade',
                               'trapezeus','facial','popliteal', 'talonavicular', 'thenar','myofascial'])
        anatomy_dict.update(terms)

        amatcher_simple = DictionaryMatch(d=anatomy_dict, ignore_case=True)
        locations = set(['L', 'L hand', 'R', 'R hand', 'anterior', 'bilateral', 'caudal',
                         'contralateral', 'crania', 'distal', 'dorsal', 'inferior',
                         'inner', 'ipsilateral', 'l', 'l.', 'lateral', 'L>R', 'R > L',
                         '(L)', '(R)', '( L )', '( R )', 'plantar',
                         'left', 'left sided', 'left-sided', 'low', 'lower',
                         'medial', 'mid', 'outer', 'posterior', 'proximal',
                         'r', 'r.', 'right', 'right sided', 'right-sided',
                         'superior', 'terminal', 'upper', 'ventral',
                         'quadrant', 'substernal', 'suprapubic'])

        # adverb version
        locations = set(["{}ly".format(t) for t in locations] + ["cranially"]).union(locations)
        locations = sorted(locations,key=len,reverse=1)
        locations = [t.replace("-","\-") for t in locations]

        rgx = "(%s){1,4}" % "|".join(locations).lower()
        spatial_mod_matcher = RegexMatchEach(rgx=rgx)

        #spatial_mod_matcher = DictionaryMatch(d=dict.fromkeys(locations), ignore_case=True)

        # directional modifiers
        directional = set(["axial", "intermediate", "parietal", "visceral"])
        directional = set(["{}ly".format(t) for t in directional]).union(directional)

        rgx = "(%s){1,3}" % "|".join(directional).lower()
        directional_mod_matcher = RegexMatchEach(rgx=rgx)

        #directional_mod_matcher = DictionaryMatch(d=dict.fromkeys(directional), ignore_case=True)

        left_location_matcher = Concat(spatial_mod_matcher, amatcher_simple,
                                       left_required=False, right_required=True)

        right_location_matcher = Concat(amatcher_simple, spatial_mod_matcher,
                                        left_required=True, right_required=False)

        left_direction_matcher = Concat(directional_mod_matcher, amatcher_simple,
                                        left_required=False, right_required=True)

        rgx = "[SsLlTt][0-9]+\s*[-]\s*[SsLlTt][0-9]+"
        vertebrae_range_matcher = RegexMatchSpan(rgx=rgx, ignore_case=True)

        children = [left_direction_matcher,
                    right_location_matcher,
                    left_location_matcher,
                    vertebrae_range_matcher]

        return children


class PainMatcher(Union):

    def __init__(self, dictionary, longest_match_only=True):

        self.dictionary = dictionary
        self.longest_match_only = longest_match_only
        self.children = self._init_matchers()

    def _init_matchers(self):

        # create nociception dictionary matcher
        MF_dict_pain = DictionaryMatch(d=self.dictionary, ignore_case=True,
                                       longest_match_only=self.longest_match_only)

        # Pain:
        rgx = "pain\s*(score|level)*\s*[:]*\s*[0-9][.+-]*[0-9]*[/][0-9]+"
        #rgx = "(pain\s*[:]\s*)*pain\s*(score|level)*\s*[:]*\s*[0-9][.+-]*[0-9]*[/][0-9]+"
        MF_pain_scores = RegexMatchSpan(rgx=rgx, ignore_case=True)

        # 8/10 pain
        rgx = "[0-9][.+-]*[0-9]*[/][0-9]+\spain"
        MF_pain_right_scores = RegexMatchSpan(rgx=rgx, ignore_case=True)

        return [MF_dict_pain, MF_pain_scores, MF_pain_right_scores]

