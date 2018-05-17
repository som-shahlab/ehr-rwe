from .relation import *
from ..negex import *
from ..utils import load_dict

from snorkel.lf_helpers import *
from ddbiolib.ontologies.umls import UmlsNoiseAwareDict


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

def all_seq_dict_matches(tokens, dictionary, min_len=3):
    """
    TODO - merge this with all_dict_matches
    """
    m = {}
    for i in range(0, len(tokens)):
        for j in range(0, len(tokens)):
            if i > j:
                continue
            span = " ".join(tokens[i:j])
            if span.lower() in dictionary and len(span) > min_len:
                m[span.lower()] = (i,j)
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

    def __init__(self, candidates, data_root="../../data/"):
        """

        :param candidates:
        """
        super(AnatomyPainRelation, self).__init__('anatomy-pain')
        self.candidates = candidates
        self.data_root = data_root
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
        return pref_set

    def _init_deps(self):

        negex = NegEx("{}dicts/negex".format(self.data_root))

        dict_symptoms = set(['fever', 'cough', 'chest pain', 'rigors', 'nausea', 'vomitting', 'night sweats',
                             'headache', 'weight loss', 'SOB', 'chest pain', 'pressure', 'palpitations',
                             'shortness of breath', 'abdominal pain', 'constipation', 'diarrhea', 'muscle aches',
                             'joint pains', 'rash', 'dysuria'])

        accept_headers = set(['CHIEF COMPLAINT', 'IMPRESSION', 'HISTORY OF PRESENT ILLNESS',
                              'ROS', 'FINAL REPORT INDICATION','ASSESSMENT AND PLAN', 'REASON FOR HOSPITALIZATION',
                              'HOSPITAL COURSE', 'CLINIC NOTE', 'ASSESSMENT AND PLAN', 'CONDITION AT DISCHARGE'])

        reject_headers = set(['PAST MEDICAL HISTORY', 'DISCHARGE INSTRUCTIONS', 'PHYSICAL EXAMINATION',
                              'UNDERLYING MEDICAL CONDITION', 'CTA CARD', 'REVIEW OF SYSTEMS'])

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

        dict_pain = load_dict("{}dicts/nociception/nociception.curated.txt".format(self.data_root))
        dict_anatomy = load_dict("{}dicts/anatomy/fma_human_anatomy.bz2".format(self.data_root))

        umls_terms = UmlsNoiseAwareDict(positive=['Sign or Symptom'], name="terms", ignore_case=True)
        dict_sign_or_symptom = umls_terms.dictionary()

        sent_cands = build_sentence_candidates(self.candidates)
        pref_arg_set = self._build_pref_arg_set(sent_cands)

        #
        # Domain Functions
        #
        # These are helper functions that we invoke from within labeling functions.


        def contains_prepositional_phrase(c):
            rgx = "(from|over|around|between|in|to|on) (the|both)"
            s = " ".join(get_between_tokens(c)).lower()
            return True if re.search(rgx, s) else False

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

        def long_term_history_of(c):
            """
            15+ year history of
            """
            head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
            left = " ".join(get_left_tokens(head, window=10))
            v = re.search("[0-9]{1,2}\s*[+-]*\s*year history of", left)
            return True if v != None else False

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
            v = chronic_pain(c, window=3)
            v &= pref_arg_attachment(c)
            v &= not history_of(c)
            return 1 if v else 0

        def LF_history_of(c):
            """
            Check the left-hand context for terms indicating historical statements
            e.g., 'history of chest pain'
            """
            v = history_of(c)
            header = get_header(c)

            v &= not long_term_history_of(c)
            v &= not chronic_pain(c, window=3)
            v &= header not in ['HISTORY OF PRESENT ILLNESS', 'PLAN']
            return -1 if v else 0

        def LF_long_term_history_of(c):
            """
            Check the left-hand context for terms indicating historical statements
            e.g., 'history of chest pain'
            """
            return 1 if long_term_history_of(c) else 0

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
            span = " ".join(get_between_tokens(c)).lower()
            if not span:
                return 0
            v = span == "is" or re.search("there is|is experiencing",span) != None or span.split()[-1] == "is"
            v &= not long_distance_attachment(c)
            v &= not negated(c)
            v &= not hypothetical(c)
            v &= not pro_re_nata(c)
            v &= not denies(c)
            return 1 if v else 0

        def LF_action_verbs(c):
            """
            """
            actions = set(['radiation', 'radiating', 'radiate', 'radiates',
                           'decends', 'descending', 'decend'])
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
            return -1 if len(pain_meds.intersection(tokens)) > 0 else 0

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

            If there are other candidate headers between our arguments, we reject this candidate.
            """
            text = c.anatomy.sentence.text
            i, j = c.anatomy.char_start, c.anatomy.char_end
            v = text[min(j + 1, len(text) - 1)] in [':', ";", ")"]
            if v:
                head = c.anatomy if c.anatomy.char_start < c.pain.char_start else c.pain
                tail = c.anatomy if head != c.anatomy else c.pain
                span = text[head.char_end + 1:tail.char_start]
                rgx = re.compile("((?:[A-Z><]+\s*){1,4})(?:\s*[:])")
                headers = rgx.findall(span)
                v &= not headers
                v &= head != c.pain

            return -1 if v else 0

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
            cw = {"bowel": set(['sound']), "bone": set(['scan','graft'])}
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

        def LF_non_modifier(c):
            """
            non-tender
            :param c:
            :return:
            """
            i, j = c.pain.char_start, c.pain.char_end
            text = c.get_parent().text
            return -1 if "non" in text[i - 4:i] else 0

        def LF_contains_prepositional_phrase(c):
            """
            Prepositional phrase denoting spatial information is found between args
            e.g., "in both", "over the", etc.
            :param c:
            :return:
            """
            v = contains_prepositional_phrase(c)
            v &= not long_distance_attachment(c)
            v &= not hypothetical(c)
            v &= not denies(c)
            return 1 if v else 0

        def LF_reject_entities_inbetween(c):
            """
            """
            actions = set(['radiation', 'radiating', 'radiate', 'radiates',
                           'decends', 'descending', 'decend'])
            tokens = get_between_tokens(c)
            m = all_seq_dict_matches(tokens, dict_anatomy)
            v = len(m) > 0
            v &= len(tokens) > 0
            v &= len(actions.intersection(tokens)) == 0
            v &= not contains_prepositional_phrase(c)
            return -1 if v else 0

        # #LF_pain_spatial_modifier,
        self.lfs = [LF_pro_re_nata,
                    LF_negated,
                    LF_hypothetical,
                    LF_denies,
                    LF_history_of,
                    LF_long_term_history_of,
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
                    LF_non_modifier,
                    LF_contains_prepositional_phrase]