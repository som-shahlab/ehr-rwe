# -*- coding: utf-8 -*-

from .relation import *
from ..negex import *
from ..utils import load_dict

import bz2
import csv

from snorkel.lf_helpers import *
from ddbiolib.ontologies.umls import UmlsNoiseAwareDict


def load_negex_defs(filename):

    negex_lexicon = []
    with open(filename, 'rU') as of:
        reader = csv.reader(of, delimiter=',',)
        for row in reader:
            term = row[0]
            category = row[30]
            direction = row[32]
            if category == 'definiteNegatedExistence':
                negex_lexicon.append({'term':term, 'category':'definite', 'direction':direction})
            elif category == 'probableNegatedExistence':
                negex_lexicon.append({'term':term, 'category':'probable', 'direction':direction})
            elif category == 'pseudoNegation':
                negex_lexicon.append({'term':term,'category': 'pseudo', 'direction':direction})

    return negex_lexicon

def load_anatomy_dictionary(filename):
    manual_term_list = ["abd", "abdominal", "costovertebral"]
    anatomyterms = [line.strip().lower() for line in bz2.BZ2File(filename, 'rb').readlines() if line.strip() != "" and len(line.strip()) > 1 and line.strip().lower() not in stopwords]
    anatomyterms += manual_term_list
    return anatomyterms

def get_between_tokens(c, attrib='words'):
    """
    Overrride's Snorkel's default implementation of this function

    :param c:
    :param attrib:
    :return:
    """
    args = (c[0], c[1]) if c[0].char_start < c[1].char_start else (c[1], c[0])
    start, end = c[0].char_to_word_index(args[0].char_end), c[1].char_to_word_index(args[1].char_start)
    tokens = c[0].sentence.__dict__[attrib]
    return tokens[start + 1:end]

def build_sentence_candidates(cands):
    """
    Group candidates by sentence ID
    :param cands:
    :return:
    """
    sent_cands = defaultdict(list)
    for c in cands:
        sent_cands[c[0].sentence.id].append(c)
    return sent_cands

def all_dict_matches(cand, dictionary):
    """
    """
    m = {}
    char_offsets = cand[0].sentence.char_offsets
    text = cand[0].sentence.text
    words = cand[0].sentence.words

    for i in range(0, len(cand[0].sentence.words)):
        start = char_offsets[i]
        for j in range(0, len(cand[0].sentence.words)):
            if i > j:
                continue
            end = char_offsets[j] + len(words[j])
            span = text[start:end]
            if span.lower() in dictionary:
                m[span.lower()] = (start, end)
    return m

def compound_word(c, arg_order=(1, 0)):
    """
    Identify compound mentions with some argument ordering, e.g.,

    chest pain   [ANATOMY|PAIN]  arg order 1,0
    neck pain    [ANATOMY|PAIN]  arg order 1,0
    tender back  [PAIN|ANATOMY]  arg order 0,1

    :param c:
    :param arg_order:
    :return:
    """
    tokens = get_between_tokens(c)
    if tokens:
        return False
    args = (c[arg_order[0]], c[arg_order[1]])
    return args[0].char_start < args[1].char_start


class AnatomyPainRelation(LabelingFuncGen):

    def __init__(self, candidates):
        """

        :param candidates:
        """
        super(AnatomyPainRelation, self).__init__('anatomy-pain')
        self.candidates = candidates
        self._init_deps()

    def _build_pref_arg_set(self, sent_cands):
        """
        Arguments will have preferred attachments, for example, in
        'neck [[pain]] radiating to L sided temporal and [[neck]] pain'
        the bracketed args should *not* be attached, since [[neck]] [[pain]]
        is a preferred relation.
        This function determines all such claimed arg pairs in a sentence.

        :param sent_cands:
        :return:
        """
        pref_set = {}
        for uid in sent_cands:
            # exclude all relations that attach to compound word spans
            cw = {cand: 1 for cand in sent_cands[uid] if compound_word(cand)}
            cw_spans = {s: 1 for cand in cw for s in cand}

            # if any span attaches to a compound word, reject this attachment
            d = {cand.id: True for cand in cw}
            for cand in sent_cands[uid]:
                if cand in cw:
                    continue
                if cand[0] not in cw_spans and cand[1] not in cw_spans:
                    d[cand.id] = True
            pref_set[uid] = d

            print len(sent_cands[uid]), len(pref_set[uid])
        return pref_set

    def _init_deps(self):

        negex = NegEx("../data/dicts/negex")

        anat_dictfile = "../data/dicts/anatomy/fma_human_anatomy.bz2"
        anatomy_terms = load_anatomy_dictionary(anat_dictfile)

        negex_lexicon_file = "../data/dicts/negex/negex_multilingual_lexicon-en-de-fr-sv.csv"
        negex_lexicon = load_negex_defs(negex_lexicon_file)

        dict_symptoms = set(['fever', 'cough', 'chest pain', 'rigors', 'nausea', 'vomitting', 'night sweats',
                             'headache', 'weight loss', 'SOB', 'chest pain', 'pressure', 'palpitations',
                             'shortness of breath', 'abdominal pain', 'constipation', 'diarrhea', 'muscle aches',
                             'joint pains', 'rash', 'dysuria'])

        accept_headers = set(['CHIEF COMPLAINT', 'IMPRESSION', 'HISTORY OF PRESENT ILLNESS',
                              'REVIEW OF SYSTEMS', 'ROS', 'FINAL REPORT INDICATION',
                              'CONDITION AT DISCHARGE'])
        reject_headers = set(['PAST MEDICAL HISTORY', 'DISCHARGE INSTRUCTIONS',
                              'UNDERLYING MEDICAL CONDITION', 'CTA CARD'])

        # see 'Qualitative Concept', 'Finding', 'Sign or Symptom'
        dict_intensity = set(['sharp', 'intense', 'extreme', 'worsening', 'moderate', 'minimal', 'moderate',
                              'mild', 'significant', 'crushing', 'severe', 'excruciating', 'slight',
                              'unbearable'])

        dict_nsaids = set(['aproxen', 'aleve', 'anaprox', 'naprelan', 'naprosyn', 'aspirin', 'tylenol',
                           'ibuprofen', 'motrin', 'advil', 'celecoxib', 'celebrex', 'acetaminophen'])

        dict_narcotics = set(['codeine', 'hydrocodone', 'zohydro er', 'oxycodone', 'oxycontin',
                              'roxicodone', 'methadone', 'hydromorphone', 'dilaudid', 'exalgo',
                              'morphine', 'avinza', 'kadian', 'msir', 'ms contin', 'fentanyl',
                              'actiq', 'duragesic'])

        dict_stopwords = set(['MD', 'B6', 'B12'])

        dict_emergency_instructions = set(['seek medical attention', 'go to the emergency room', 'please call'])

        dict_findings = ['nondistended', 'soft', 'distended', 'erythema', 'swelling']

        dict_spatial = set(['L', 'L hand', 'R', 'R hand', 'anterior', 'bilateral', 'caudal',
                            'contralateral', 'crania', 'distal', 'dorsal', 'inferior',
                            'inner', 'ipsilateral', 'l', 'l.', 'lateral',
                            'left', 'left sided', 'left-sided', 'low', 'lower',
                            'medial', 'mid', 'outer', 'posterior', 'proximal',
                            'r', 'r.', 'right', 'right sided', 'right-sided',
                            'superior', 'terminal', 'upper', 'ventral',
                            'quadrant', 'substernal', "axial", "intermediate", "parietal", "visceral"])

        dict_pain = load_dict("../data/dicts/nociception/nociception.curated.txt")

        umls_terms = UmlsNoiseAwareDict(positive=['Sign or Symptom'], name="terms", ignore_case=True)
        dict_sign_or_symptom = umls_terms.dictionary()

        sent_cands = build_sentence_candidates(self.candidates)
        pref_arg_set = self._build_pref_arg_set(sent_cands)

        #
        # Domain Functions
        #
        # These are helper functions that we invoke from within labeling functions.

        def get_header(c, sent_window=2):
            """
            Check for a medical header pattern (i.e., all capitals
            followed by a colon) within a window of n sentences

            :param c:
            :param sent_window:
            :return:
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            doc = head.sentence.document
            idx = head.sentence.position
            rgx = re.compile("^(([A-Z]+\s*){1,4})[:]")
            for i in range(idx, max(0, idx - sent_window - 1), -1):
                m = rgx.search(doc.sentences[i].text)
                if m:
                    return m.group(1)
            return None

        def pain_match(span):
            """
            Match 'pain' argument in relation candidate
            """
            rgx = "pain\s*(score|level)*\s*[:]*\s*[0-9][.+-]*[0-9]*[/][0-9]+"
            text = mention(span).lower()
            return True if re.search(rgx, text) or text in dict_pain else False

        def anatomy_match(span, validate_span=True):
            """
            Match 'anatomy' argument in relation candidate
            :param validate_span: check if there are dropped prefixes
            """
            pass

        def pref_arg_attachment(c):
            """
            """
            uid = c[0].sentence.id
            if uid not in pref_arg_set:
                return False
            return True if c.id in pref_arg_set[uid] else False

        def long_distance_attachment(c, window=10):
            tokens = get_between_tokens(c)
            return True if len(tokens) >= window else False

        def chronic_pain(c, window=1):
            """
            Check for a 'chronic' modifier of pain
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = [" ".join(get_left_tokens(head, window=1)).lower()]
            left.append(" ".join(get_left_tokens(c.pain, window=window)).lower())
            return True if 'chronic' in left else False

        def negated(c):
            """
            Use NegEx to test for *any* negation type, using the head arg as anchor
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            tail = c.anatomy if head != c.anatomy else c.pain
            ntypes = negex.all_negations(head, window=5)

            v = len(ntypes) > 0 or head.sentence.words[0].lower() in ['no']
            return True if v else False

        def hypothetical(c):
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = " ".join(get_left_tokens(head, window=50))
            m = re.search(r"((if|should) (you|she|he)|(she|he|you) (might|could|may)|if)(?:\s|$)", left)
            return True if m else False

        def denies(c):
            """
            patient (denied|denies), etc.
            Check entire left-hand of sentence
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = " ".join(get_left_tokens(head, window=50))
            m = re.search(r"(denies|denied|deny)", left)
            return True if m else False

        def history_of(c):
            """
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = " ".join(get_left_tokens(head, window=5))
            m = re.search(r"(history of)", left)
            return True if m else False

        def pro_re_nata(c):
            """
            PRN - 'use when necessary'
            This implies a *hypothetical* future event
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = " ".join(get_left_tokens(head, window=50))
            m = re.search(r"(prn|p\.r\.n\.|PRN|P\.R\.N\.|as needed|if needed)(?:\s|$)", left)
            return True if m else False

        #
        # LFs
        #

        def LF_long_distance_attachment(c):
            return -1 if long_distance_attachment(c) else 0

        def LF_pref_arg_attachment(c):
            """
            """
            uid = c[0].sentence.id
            return -1 if not pref_arg_attachment(c) else 0

        def LF_compound_words(c):
            """
            flank pain, chest pain, abdominal pain
            """
            v = compound_word(c)
            v &= not long_distance_attachment(c)
            v &= not negated(c)
            v &= not hypothetical(c)
            v &= not pro_re_nata(c)
            v &= not denies(c)
            v &= not history_of(c)
            return 1 if v else 0

        def LF_denies(c):
            """
            Patient denies some symptoms
            """
            return -1 if denies(c) else 0

        def LF_hypothetical(c):
            """
            Check the left-hand context for terms indicating hypothetical statements,
            e.g., 'if you'
            """
            return -1 if hypothetical(c) else 0

        def LF_temporal_recent(c):
            """
            """
            temporal_terms = set(['now', 'recent', 'current', 'presently', 'recently', 'new'])
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = map(lambda x: x.lower(), get_left_tokens(head, window=5))
            v = len(temporal_terms.intersection(left)) > 0
            v &= pref_arg_attachment(c)
            #     v &= not long_distance_attachment(c)
            #     v &= not negated(c)
            #     v &= not hypothetical(c)
            #     v &= not pro_re_nata(c)
            #     v &= not denies(c)
            return 1 if v else 0

        def LF_pro_re_nata(c):
            """
            Check the for PRN ('as needed') drug usage. Reject these
            candidates *unless* they refer to chronic pain
            """
            v = pro_re_nata(c)
            v &= not chronic_pain(c, window=3)
            return -1 if v else 0

        def LF_negated(c):
            """
            Check the left-hand context for terms indicating hypothetical statements,
            e.g., 'if you'
            """
            return -1 if negated(c) else 0

        def LF_chronic_pain(c):
            """
            chronic back pain
            chronic pain of the hip
            """
            return 1 if chronic_pain(c, window=3) else 0

        def LF_history_of(c):
            """
            Check the left-hand context for terms indicating historical statements
            e.g., 'history of chest pain'
            """
            return -1 if history_of(c) else 0

        def LF_breaking_char_inbetween(c):
            """
            Mentions with a comma or semicolon are less likely to reflect
            real argument attachments
            """
            tokens = get_between_tokens(c)
            if not tokens:
                return 0
            return -1 if len(set([";", ","]).intersection(tokens)) > 0 else 0

        def LF_instructions(c):
            """
            Emergency instructions (indicates boilerplate text)
            'go to the emergency room','please call', 'seek medical attention', etc.

            TODO: make this more efficient that linear search(trie matching)
                  mine other phrases
            """
            text = c[0].sentence.text.lower()
            for key_phrase in dict_emergency_instructions:
                if key_phrase in text:
                    return -1
            return 0

        def LF_list_side_effects(c):
            """
            Mention occurs in list of symptoms, e.g.,

            'if you experience worsening chest pain, shortness of breath, nausea,
            vomiting, diarrhea, abdominal pain, or any other concerning symptom'

            Use UMLS 'Sign or Symptom' and custom term dictionaries
            """
            matches = all_dict_matches(c, dict_symptoms)
            matches.update(all_dict_matches(c, dict_sign_or_symptom))
            text = c[0].sentence.text
            num_delim = 0
            for term in matches:
                i, j = matches[term]
                if text[min(j, len(text) - 1)] in [';', ',']:
                    num_delim += 1

            v = num_delim > 2  # at least 3 side effect mentions
            v &= compound_word(c)
            v &= hypothetical(c)
            return -1 if v else 0

        def LF_past_perfect_tense(c):
            """
            had
            had been
            """
            tokens = " ".join(get_between_tokens(c))
            v = re.search("(had been|had)(?:\s|$)", tokens) != None
            v &= not long_distance_attachment(c)
            v &= not negated(c)
            v &= not hypothetical(c)
            v &= not pro_re_nata(c)
            v &= not denies(c)
            return -1 if v else 0

        def LF_linking_verbs(c):
            """
            """
            tokens = get_between_tokens(c)
            v = "is" in tokens
            v &= not long_distance_attachment(c)
            v &= not negated(c)
            v &= not hypothetical(c)
            v &= not pro_re_nata(c)
            v &= not denies(c)
            return 1 if v else 0

        def LF_action_verbs(c):
            """
            """
            actions = set(['radiation', 'radiate', 'descending', 'decend'])
            tokens = get_between_tokens(c, 'lemmas')

            v = len(actions.intersection(tokens)) > 0
            return 1 if v else 0

        def LF_stopwords(c):
            """
            Reject common stopwords, e.g., 'MD', 'Vitamin B12'
            """
            s1, s2 = c[0].get_span(), c[1].get_span()
            return -1 if s1 in dict_stopwords or s2 in dict_stopwords else 0

        def LF_intensity(c):
            """
            Mention of pain is precededed
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = [" ".join(get_left_tokens(head, window=1)).lower()]
            left.append(" ".join(get_left_tokens(c.pain, window=1)).lower())

            v = len(dict_intensity.intersection(left)) > 0
            v &= not long_distance_attachment(c)
            v &= not negated(c)
            v &= not hypothetical(c)
            v &= not pro_re_nata(c)
            v &= not denies(c)
            return 1 if v else 0

        def LF_pain_meds(c):
            """
            Sentence contains mention of common pain medications, e.g., NSAIDs and narcotics
            """
            pain_meds = dict_narcotics.union(dict_nsaids)
            tokens = map(lambda x: x.lower(), c[0].sentence.words)
            return 1 if len(pain_meds.intersection(tokens)) > 0 else 0

        def LF_pain_spatial_modifier(c):
            """
            Candidate relation has some spatial modifiers between args, e.g.,

             '[[pain]] under her [[right breast]]'
             '[[tenderness]] in the right side of the [[abdomen]]'
            """
            args = (c.pain, c.anatomy)
            v = args[0].char_start < args[1].char_start
            tokens = get_between_tokens(c)
            if not tokens:
                return 0

            v &= pref_arg_attachment(c)
            v &= len(dict_spatial.intersection(tokens)) > 0
            v &= not long_distance_attachment(c)
            v &= not negated(c)
            v &= not hypothetical(c)
            v &= not pro_re_nata(c)
            return 1 if v else 0

        def LF_arg_is_header(c):
            """
            Arg is a header (i.e., a span followed by a header delimitter like a colon)

            'Left Shoulder: 10/10 Pain scale'
            'ABD: distended, tender to touch'

            If there are other candidate headers between our aguments, we reject this candidate.
            """
            text = c.anatomy.sentence.text
            i, j = c.anatomy.char_start, c.anatomy.char_end
            v = text[min(j + 1, len(text) - 1)] in [':', ")", ";"]
            if v:
                head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
                tail = c.anatomy if head != c.anatomy else c.pain
                span = text[head.char_end + 1:tail.char_start]
                rgx = re.compile("((?:[A-Z><]+\s*){1,4})(?:\s*[:])")
                headers = rgx.findall(span)
                v &= not headers
            return 1 if v else 0

        def LF_wsd_back(c):
            """
            Disambiguate usage of 'back'
            TODO: CoreNLP POS tags 'back pain' incorrectly, idenfiying 'back' as an adverb
            """
            rgx = '(call[s]*|c[ao]me[s]*|turn[s]*)'
            left = " ".join(get_left_tokens(c.anatomy, window=1)).lower()
            return -1 if re.search(rgx, left, re.I) else 0

        def LF_wsd_anatomy_compound_words(c):
            """
            Reject anatomy words that don't refer to actual locations
            but location attributes or procedures

            'bowel sounds','bone scan'
            """
            cw = {"bowel": set(['sound']), "bone": set(['scan'])}
            term = c.anatomy.get_span().lower()
            if term not in cw:
                return 0
            right = " ".join(get_right_tokens(c.anatomy, window=1, attrib='lemmas'))
            return -1 if right in cw[term] else 0

        def LF_accept_header(c):
            """
            Mention occurs under a medical heading that correlates with
            positive mentions.
            """
            header = get_header(c)
            v = header in accept_headers
            v &= not denies(c)
            v &= not negated(c)
            v &= not hypothetical(c)
            v &= not history_of(c)
            v &= pref_arg_attachment(c)  # doesn't attach to a compound word mention
            return 1 if v else 0

        def LF_reject_header(c):
            header = get_header(c)
            v = header in reject_headers
            return -1 if v else 0

        def LF_a_too_far_apart(c):
            return -1 if (len(get_between_tokens(c)) > 10 and c.pain.char_end > c.anatomy.char_end) or ((len(get_between_tokens(c)) > 16 and c.pain.char_end < c.anatomy.char_end)) else 0


        def LF_a_too_far_apart_less(c):
            return -1 if (len(get_between_tokens(c)) > 5 and c.pain.char_end > c.anatomy.char_end) or ((len(get_between_tokens(c)) > 8 and c.pain.char_end < c.anatomy.char_end)) else 0


        def LF_a_contiguous_right_pain(c):
            '''Compound mentions, e.g., "chest pain", "neck pain" '''
            return 1 if len(get_between_tokens(c)) < 1 and c.pain.char_end > c.anatomy.char_end else 0


        def LF_a_contiguous_right_pain_no_negex(c):
            '''Compound mentions, e.g., "chest pain", "neck pain" '''
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']
            longest = len(max(possible_terms, key=len))
            left_window = get_left_tokens(c, window=longest+2)
            left_window_phrase = ' '.join(left_window)
            flag = None
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                if result is not None:
                    flag = -1
            return 1 if len(get_between_tokens(c)) < 1 and c.pain.char_end > c.anatomy.char_end and flag is None else 0


        def LF_a_near_contiguous_right_pain(c):
            between_tokens = get_between_tokens(c)
            return 1 if len(between_tokens) < 10 and (',' in between_tokens or 'and' in between_tokens) and c.pain.char_end > c.anatomy.char_end else 0


        from snorkel.utils import tokens_to_ngrams
        def LF_a_near_contiguous_right_pain_no_negex(c):

            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']

            longest = len(max(possible_terms, key=len))
            left_window = get_left_tokens(c, window=longest+2)
            left_window_phrase = ' '.join(left_window)+' '
            right_window = get_right_tokens(c, window=3)
            right_window_phrase = ' '.join(right_window)+' '
            between_tokens = get_between_tokens(c)

            f = (lambda w: w.lower())
            between_terms = [ngram for ngram in tokens_to_ngrams(map(f, c.pain.get_parent()._asdict()['words'][c.anatomy.get_word_start():c.pain.get_word_start()+1]), n_max=1)]
            between_phrase = ' '.join(between_terms)+' '
            negation_flag = None
            pain_flag = None
            right_anatomy_flag = None

            list_flag = LF_a_candidate_in_list(c)

            for aterm in anatomy_terms:
                if aterm in right_window_phrase:
                    right_anatomy_flag = -1

            misattached_flag = None
            misattached_flag_1 = LF_a_misattached_entities(c)
            misattached_flag_3 = LF_a_misattached_entities_v3(c)

            odd_flag = None
            odd_list = ["flexion", "regimen", "raise"]

            for oe in odd_list:
                if oe in between_phrase:
                    odd_flag = -1

            if misattached_flag_1 == -1 or misattached_flag_3 == -1:
                misattached_flag = -1

            for pt in possible_terms:
                pattern = '\s'.join(pt)+'[-\s]*'

                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                result2 = matcher.search(between_phrase)
                if result is not None or result2 is not None:
                    negation_flag = -1
            for nterm in dict_pain:
                if nterm in between_tokens or nterm in left_window:
                    pain_flag = -1
            if len(between_tokens) < 10 and (',' in between_tokens or 'and' in between_tokens) and c.pain.char_start > c.anatomy.char_end and negation_flag != -1 and pain_flag is None and list_flag != -1 and misattached_flag is None and odd_flag != -1:
                return 1
            else:
                return 0

        def LF_a_anatomy_between_tokens(c):
            between_tokens = get_between_tokens(c)
            anat_flag = None
            pain_flag = None
            if len(between_tokens) < 10 and (',' in between_tokens or 'and' in between_tokens) and '(' not in between_tokens and ';' not in between_tokens and c.pain.char_start > c.anatomy.char_end:
                for term in between_tokens:
                    if term in anatomy_terms:
                        anat_flag = 1
                for term in between_tokens:
                    if term in dict_pain:
                        pain_flag = -1
            return 1 if anat_flag is not None and pain_flag is None else 0

        def LF_a_contiguous_left_pain(c):

            return 1 if len(get_between_tokens(c)) < 1 and c.pain.char_end < c.anatomy.char_end else 0

        def LF_a_near_contiguous_left_pain(c):
            possible_terms = [x['term'] for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']

            '''Non-contiguous but close mentions, e.g., "pain in the hip", "tenderness of the right side" '''
            between_tokens = get_between_tokens(c)
            right_window = get_right_tokens(c, window=3)
            left_window = get_left_tokens(c, window = 8)
            left_window_phrase = ' '.join(left_window)
            negation_flag = None
            for term in possible_terms:
                if term in left_window:
                    negation_flag = -1
            second_pain_flag = None
            for term in right_window:
                if term in dict_pain:
                    second_pain_flag = -1
            #used to be < 3
            return 1 if len(between_tokens) < 3 and second_pain_flag is None and negation_flag is None and '(' not in between_tokens and ',' not in between_tokens and c.pain.char_end < c.anatomy.char_start else 0

        def LF_a_long_distance_left_pain(c):
            between_tokens = get_between_tokens(c)
            left_window = get_left_tokens(c, 3)
            right_window = get_right_tokens(c, 3)
            pain_flag = None
            anat_flag = None
            for nterm in dict_pain:
                if nterm in right_window:
                    pain_flag = -1

            for aterm in anatomy_terms:
                if aterm in left_window:
                    anat_flag = -1

            return 1 if c.pain.char_end < c.anatomy.char_start and len(between_tokens) < 15 and pain_flag is None and anat_flag is None else 0

        def LF_a_long_distance_left_pain_no_negex(c):
            between_tokens = get_between_tokens(c)
            between_phrase = ' '.join(between_tokens)+' '
            left_window = get_left_tokens(c, 5)
            right_window = get_right_tokens(c, 3)
            left_window_phrase = ' '.join(left_window) + ' '
            pain_flag = None
            anat_flag = None
            anat_between_flag = None
            negation_flag = None
            for nterm in dict_pain:
                if nterm in right_window or nterm in between_tokens:
                    pain_flag = -1

            for aterm in anatomy_terms:
                if aterm in left_window:
                    anat_flag = -1
                if aterm in between_phrase and "," not in between_phrase:
                    anat_between_flag = -1
            date_flag = LF_a_date_between(c)

            list_flag = LF_a_candidate_in_list(c)

            ma_flag  = LF_a_left_pain_multiple_anat(c)

            tfa_flag = LF_a_too_far_apart(c)

            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                if result is not None:
                    negation_flag = -1
            if c.pain.char_end < c.anatomy.char_start and len(between_tokens) < 10 and pain_flag is None and anat_flag is None and negation_flag is None and date_flag != -1 and list_flag != -1 and ma_flag != -1:
                return 1
            else:
                return 0


        def LF_a_long_distance_left_pain_no_negex_v2(c):
            between_tokens = get_between_tokens(c)
            between_phrase = ' '.join(between_tokens)+' '
            left_window = get_left_tokens(c, 5)
            right_window = get_right_tokens(c, 3)
            left_window_phrase = ' '.join(left_window) + ' '
            pain_flag = None
            anat_flag = None
            anat_between_flag = None
            negation_flag = None
            for nterm in dict_pain:
                if nterm in right_window or nterm in between_tokens:
                    pain_flag = -1

            for aterm in anatomy_terms:
                if aterm in left_window:
                    anat_flag = -1
                if aterm in between_phrase and "," not in between_phrase:
                    anat_between_flag = -1
            date_flag = LF_a_date_between(c)

            list_flag = LF_a_candidate_in_list(c)

            ma_flag  = LF_a_left_pain_multiple_anat(c)

            tfa_flag = LF_a_too_far_apart(c)

            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                if result is not None:
                    negation_flag = -1
            if c.pain.char_end < c.anatomy.char_start and len(between_tokens) < 10 and anat_between_flag is None and pain_flag is None and anat_flag is None and negation_flag is None and date_flag != -1 and list_flag != -1 and ma_flag != -1:
                return 1
            else:
                return 0


        def LF_a_complains_of(c):
            left_window = get_left_tokens(c, window=7)
            left_window_phrase = ' '.join(left_window)
            between_tokens = get_between_tokens(c)
            #pattern = 'complain(t*|s*|ing*)\sof'
            pattern = 'complain(s*|ing*)\sof'
            matcher = re.compile(pattern, flags=re.I)
            result = matcher.search(left_window_phrase)
            flag = None
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']
            for pt in possible_terms:
                pattern2 = '\s'.join(pt)+'\s'
                matcher2 = re.compile(pattern2, flags=re.I)
                result2 = matcher2.search(left_window_phrase)
                if result2 is not None:
                    flag = -1
            if result is not None and flag is None and len(between_tokens) <= 10:
                return 1
            elif result is not None and flag is not None:
                return -1
            else:
                return 0

        def LF_a_history_of(c):
            left_window = get_left_tokens(c, window=3)
            left_window_phrase = ' '.join(left_window)
            pattern = 'history\sof'
            matcher = re.compile(pattern, flags=re.I)
            result = matcher.search(left_window_phrase)
            return -1 if result is not None else 0

        def LF_a_no_pain_between_tokens(c):
            between_tokens = get_between_tokens(c)
            if len(between_tokens) < 10 and ',' in between_tokens and '(' not in between_tokens and ';' not in between_tokens and c.pain.char_start > c.anatomy.char_end:
                for term in dict_pain:
                    if term in between_tokens:
                        return -1
            return 0

        def LF_a_negex_definite_negation_left(c):
            '''Definite negative mentions to the left of the candidate e.g. "patient denies chest pain" '''
            '''Based on Negex lexicon'''
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']
            longest = len(max(possible_terms, key=len))
            left_window = get_left_tokens(c, window=longest+2)
            left_window_phrase = ' '.join(left_window)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                if result is not None:
                    return -1
            return 0

        def LF_a_no_negex_negation_left(c):
            '''Definite negative mentions to the left of the candidate e.g. "patient denies chest pain" '''
            '''Based on Negex lexicon'''
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']
            longest = len(max(possible_terms, key=len))
            left_window = get_left_tokens(c, window=longest+2)
            left_window_phrase = ' '.join(left_window)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                if result is not None:
                    return 0
            return 1


        def LF_a_negex_probable_negation_left(c):
            '''Probable negative mentions to the left of the candidate e.g. "patient does not report chest pain" '''
            '''Based on Negex lexicon'''
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'probable' and x['direction'] == 'forward']
            longest = len(max(possible_terms, key=len))
            left_window = get_left_tokens(c, window=longest+2)
            left_window_phrase = ' '.join(left_window)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                if result is not None:
                    return -1
            return 0

        def LF_a_negex_pseudo_negation_left(c):
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'pseudo' and x['direction'] == 'forward']
            longest = len(max(possible_terms, key=len))
            left_window = get_left_tokens(c, window=longest+2)
            left_window_phrase = ' '.join(left_window)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(left_window_phrase)
                if result is not None:
                    return -1
            return 0

        def LF_a_negex_definite_negation_right(c):
            '''Definite negative mentions to the right of the candidate e.g. "chest pain is denied" '''
            '''Based on Negex lexicon'''
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'backward']
            longest = len(max(possible_terms, key=len))
            right_window = get_right_tokens(c, window=longest+2)
            right_window_phrase = ' '.join(right_window)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(right_window_phrase)
                if result is not None:
                    return -1
            return 0

        def LF_a_negex_probable_negation_right(c):
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'probable' and x['direction'] == 'backward']
            longest = len(max(possible_terms, key=len))
            right_window = get_right_tokens(c, window=longest+2)
            right_window_phrase = ' '.join(right_window)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(right_window_phrase)
                if result is not None:
                    return -1
            return 0

        def LF_a_negex_pseudo_negation_right(c):
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'probable' and x['direction'] == 'backward']
            longest = len(max(possible_terms, key=len))
            right_window = get_right_tokens(c, window=longest+2)
            right_window_phrase = ' '.join(right_window)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(right_window_phrase)
                if result is not None:
                    return -1
            return 0

        def LF_a_candidate_in_list(c):
            '''e.g. Warning Signs: fever, increased or excessive pain, redness or pus at incision/wound sites,
            vomiting, bleeding, shortness of breath, chest pain,'''
            sent_spans = get_sent_candidate_spans(c)
            sent = ''
            for span in sent_spans:
                words = span.get_parent()._asdict()['words']
                sent += ' '.join(words)
            pattern = '(\s\S+\s*,\s*){2,}'
            matcher = re.compile(pattern, flags=re.I)
            result = matcher.search(sent)

            if result is not None:
                flag = -1
            return -1 if result is not None else 0

        def LF_a_candidate_in_negative_list(c):
            '''e.g. Otherwise negative for headache, dyspnea, chest pain, abdominal pain, and dysuria.'''
            left_window = get_left_tokens(c, 10)
            left_window_phrase = ' '.join(left_window)
            sent_spans = get_sent_candidate_spans(c)
            sent = ''
            for span in sent_spans:
                words = span.get_parent()._asdict()['words']
                sent += ' '.join(words)

            pattern = '(\S+[\s\S+]*,\s*){2,}'
            matcher = re.compile(pattern, flags=re.I)
            result = matcher.search(sent)
            neg_flag = None
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite' and x['direction'] == 'forward']
            for pt in possible_terms:
                pattern2 = '\s'.join(pt)+'\s'
                matcher2 = re.compile(pattern2, flags=re.I)
                result2 = matcher2.search(left_window_phrase)
                if result2 is not None:
                    neg_flag = 1
            both_flag = None
            if result is not None and neg_flag is not None:
                both_flag = 1
            return -1 if both_flag is not None else 0


        def LF_a_candidate_in_checklist(c):
            '''e.g. ¿ a ¿ b ¿ c'''
            sent_spans = get_sent_candidate_spans(c)
            sent = ''
            for span in sent_spans:
                words = span.get_parent()._asdict()['words']
                sent += ' '.join(words)

            pattern = '(¿\s*\S+\s*){2,}'
            matcher = re.compile(pattern, flags=re.I)
            result = matcher.search(sent.encode('utf-8'))
            return -1 if result is not None else 0


        def LF_a_misattached_entities(c):
            '''e.g. chest pain, abdominal pain where candidate is pain, abdominal'''
            between_tokens = get_between_tokens(c)
            return -1 if len(between_tokens) < 3 and ',' in between_tokens else 0


        def LF_a_misattached_entities_v2(c):
            '''e.g. chest pain, abdominal pain where candidate is pain, abdominal'''
            between_tokens = get_between_tokens(c)
            right_window = get_right_tokens(c, 14)
            flag = None
            for token in right_window:
                if token in dict_pain:
                    flag = -1
            return -1 if c.pain.char_end < c.anatomy.char_start and ',' in between_tokens and flag is not None else 0


        def LF_a_misattached_entities_v3(c):
            '''e.g. dorsum of the foot, positive tenderness to the right toes '''
            between_tokens = get_between_tokens(c)
            right_window = get_right_tokens(c, 14)
            anat_flag_1 = None
            anat_flag_2 = None
            for token in right_window:
                if token in anatomy_terms:
                    anat_flag_1 = -1
            if any(anatomy_terms) not in between_tokens:
                    anat_flag_2 = -1

            # removed: and ',' not in right_window
            return -1 if c.anatomy.char_end < c.pain.char_start and ',' in between_tokens and anat_flag_1 is not None and anat_flag_2 is not None else 0


        def LF_a_negated_term_between_entities(c):
            possible_terms = [x['term'].split(' ') for x in negex_lexicon if x['category'] == 'definite']
            between_tokens = get_between_tokens(c)
            between_phrase = ' '.join(between_tokens)
            for pt in possible_terms:
                pattern = '\s'.join(pt)+'\s'
                matcher = re.compile(pattern, flags=re.I)
                result = matcher.search(between_phrase)
                if result is not None:
                    return -1
            return 0


        def LF_a_pain_score_location(c):
            between_tokens = get_between_tokens(c)
            between_phrase = ' '.join(between_tokens)
            anatomy_flag = None
            for aterm in anatomy_terms:
                if aterm in between_phrase:
                    anatomy_flag = -1
            return 1 if 'location :' in between_phrase and anatomy_flag is None else 0


        def LF_a_warning_signs_hypothetical(c):
            ''' In list of 'Warning Signs:' '''
            sent_spans = get_sent_candidate_spans(c)
            sent = ''
            for span in sent_spans:
                words = span.get_parent()._asdict()['words']
                sent += ' '.join(words)
            return -1 if 'warning signs :' in sent.lower() else 0


        def LF_a_left_pain_multiple_anat(c):
            '''
            If pain entity is not attached directly to an anatomical entity e.g. 'leg pain close to the right upper thigh'
            where candidate is 'pain'~~'upper right thigh'
            then can't be attached to another entity to the left.
            '''
            flag = None
            #sent_spans = get_sent_candidate_spans(c)
            left_window = get_left_tokens(c, 5)
            if c.pain.char_end < c.anatomy.char_start:
                for token in left_window:
                    if token in anatomy_terms:
                            flag = 1
            return -1 if flag is not None else 0


        def LF_a_left_pain_anatomy_between(c):
            '''
            Long distance pain mentions where the pain mention
            is already attached to another candidate not in a list
            '''
            between_tokens = get_between_tokens(c)
            right_window = get_right_tokens(c, 8)
            flag = None
            if c.pain.char_end < c.anatomy.char_start:
                for token in between_tokens:
                    if token in anatomy_terms and "radiates" not in between_tokens:
                        flag = -1

            return -1 if flag is not None and ',' not in between_tokens and 'and' not in between_tokens else 0


        def LF_a_positive_left(c):
            '''Positive mentions to the left of the candidate e.g. "patient positive for chest pain" '''
            left_window = get_left_tokens(c, window=5)
            left_window_phrase = ' '.join(left_window)
            if "positive" in left_window_phrase:
                    return 1
            return 0


        def LF_a_date_between(c):
            between_tokens = get_between_tokens(c)
            between_phrase = ' '.join(between_tokens)+' '
            pattern = '[0-9]{2}/[0-9]{2}/[0-9]{4}'
            matcher = re.compile(pattern, flags=re.I)
            result = matcher.search(between_phrase)

            date_flag = None
            if result is not None:
                date_flag = -1

            return -1 if date_flag is not None else 0


        def LF_a_history_of_present_illness(c):
            '''HISTORY OF PRESENT ILLNESS'''
            left_window = get_left_tokens(c, window=100)
            sent_spans = get_sent_candidate_spans(c)
            sent = ''
            for span in sent_spans:
                words = span.get_parent()._asdict()['words']
                sent += ' '.join(words)

            left_window_phrase = ' '.join(left_window)
            pattern = 'history\sof\spresent\sillness'
            matcher = re.compile(pattern, flags=re.I)
            #result = matcher.search(sent)
            result = matcher.search(left_window_phrase)
            tfa = LF_a_too_far_apart_less(c)
            ma = LF_a_left_pain_multiple_anat(c)
            if result is not None and tfa is not -1 and ma is not -1:
                return 1
            else:
                return 0


        def LF_a_past_medical_history(c):
            left_window = get_left_tokens(c, window=100)
            sent_spans = get_sent_candidate_spans(c)
            sent = ''
            for span in sent_spans:
                words = span.get_parent()._asdict()['words']
                sent += ' '.join(words)

            left_window_phrase = ' '.join(left_window)
            pattern = 'past\smedical\shistory'
            matcher = re.compile(pattern, flags=re.I)
            #result = matcher.search(sent)
            result = matcher.search(left_window_phrase)
            if result is not None:
                return -1
            else:
                return 0


        def LF_a_radiograph_view(c):
            between_tokens = get_between_tokens(c)
            between_phrase = ' '.join(between_tokens)
            if 'view' in between_phrase:
                return -1
            else:
                return 0

        self.lfs = [LF_pain_spatial_modifier,
                    LF_pro_re_nata,
                    LF_negated,
                    LF_hypothetical,
                    LF_denies,
                    LF_history_of,
                    LF_compound_words,
                    LF_pref_arg_attachment,
                    LF_long_distance_attachment,
                    LF_accept_header,
                    LF_reject_header,
                    LF_breaking_char_inbetween,
                    LF_chronic_pain,
                    LF_pain_meds,
                    LF_intensity,
                    LF_past_perfect_tense,
                    LF_linking_verbs,
                    LF_action_verbs,
                    LF_list_side_effects,
                    LF_instructions,
                    LF_stopwords,
                    LF_arg_is_header,
                    LF_wsd_back,
                    LF_temporal_recent,
                    LF_wsd_anatomy_compound_words,
                    LF_a_too_far_apart,
                    LF_a_contiguous_right_pain_no_negex,
                    LF_a_contiguous_left_pain,
                    LF_a_near_contiguous_right_pain_no_negex,
                    LF_a_near_contiguous_left_pain,
                    LF_a_complains_of,
                    LF_a_no_pain_between_tokens,
                    LF_a_negex_definite_negation_left,
                    LF_a_negex_definite_negation_right,
                    LF_a_candidate_in_list,
                    LF_a_misattached_entities,
                    LF_a_misattached_entities_v2,
                    LF_a_misattached_entities_v3,
                    LF_a_candidate_in_checklist,
                    LF_a_left_pain_multiple_anat,
                    LF_a_negated_term_between_entities,
                    LF_a_pain_score_location,
                    LF_a_long_distance_left_pain_no_negex,
                    LF_a_warning_signs_hypothetical,
                    LF_a_left_pain_anatomy_between,
                    LF_a_date_between,
                    LF_a_history_of_present_illness,
                    LF_a_past_medical_history,
                    LF_a_radiograph_view]