# coding=utf-8

import re

from rwe.extractlib.utils import load_dict
from rwe.extractlib.negex import *

from snorkel.lf_helpers import *

dict_pain = load_dict("../data/supervision/dicts/nociception/nociception.curated.txt")
dict_anatomy = load_dict("../data/supervision/dicts/anatomy/fma_human_anatomy.bz2")

negex = NegEx("../data/supervision/dicts/negex")

def regex_in_text(regex, text):
    """
    Check for occurrences of regex in text

    :param regex: a regular expression
    :param text: free text
    :return: boolean; True if regex is matched text, False otherwise
    """

    matcher = re.compile(regex, flags=re.I)
    result = matcher.search(text)
    return True if result is not None else False

def text_contains_pain_mention(text):
    """
    Check for occurrences of any pain dictionary term in text

    :param text: free text
    :return: boolean; True if any pain dictionary term is found in text, False otherwise
    """

    b = any(term in text for term in dict_pain)

    return b

def text_contains_anatomy_mention(text):
    """
    Check for occurrences of any anatomy dictionary term in text

    :param text: free text
    :return: boolean; True if any pain dictionary term is found in text, False otherwise
    """

    b = any(term in text for term in dict_anatomy)

    return b

def list_contains_pain_mention(list):
    """
    Check for occurrences of any member of list in pain dictionary

    :param list: a list of tokens
    :return: boolean; True if any member of list is found in pain dictionary, False otherwise
    """
    b = any(term in dict_pain for term in list)

    return b

def list_contains_anatomy_mention(list):
    """
    Check for occurrences of any member of list in anatomy dictionary

    :param list: a list of tokens
    :return: boolean; True if any member of list is found in anatomy dictionary, False otherwise
    """

    b = any(term in dict_anatomy for term in list)

    return b

def far_apart(c):
    """
    Check for anatomy and pain entities in a pain-anatomy candidate that are
    more than 10 words apart if anatomy mention is first
    or more than 16 words apart if pain mention is first

    :param c: pain-anatomy candidate
    :return: boolean; True if anatomy and pain entities are far apart, False otherwise
    """
    distance = len(list(get_between_tokens(c)))

    b1 = distance > 10
    b1 &= c.pain.char_end > c.anatomy.char_end

    b2 = distance > 16
    b2 &= c.pain.char_end < c.anatomy.char_end

    b = b1 or b2

    return True if b else False

def less_far_apart(c):
    """
    Check for anatomy and pain entities in a pain-anatomy candidate that are
    more than 5 words apart if anatomy mention is first
    or more than 8 words apart if pain mention is first

    :param c: pain-anatomy candidate
    :return: boolean; True if anatomy and pain entities are less far apart, False otherwise
    """

    distance = len(list(get_between_tokens(c)))

    b1 = distance > 5
    b1 &= c.pain.char_end > c.anatomy.char_end

    b2 = distance > 8
    b2 &= c.pain.char_end < c.anatomy.char_end

    b = b1 or b2

    return True if b else 0

def candidate_in_list(c):
    """
    Check whether a pain-anatomy candidate is in a list e.g.
    'Warning Signs: fever, increased or excessive pain, redness or pus at incision/wound sites,
        vomiting, bleeding, shortness of breath, chest pain,'

    :param c: pain-anatomy candidate
    :return: boolean; True if candidate is in a list, False otherwise
    """

    sent_spans = get_sent_candidate_spans(c)
    sent = ''
    for span in sent_spans:
        words = span.get_parent()._asdict()['words']
        sent += ' '.join(words)

    pattern = '(\s\S+\s*,\s*){2,}'

    b = regex_in_text(pattern, sent)

    return True if b else False

def candidate_in_checklist(c):
    """
    Check whether a  pain-anatomy candidate is
    in a checklist e.g. e.g. ¿ a ¿ b ¿ c

    :param c: pain-anatomy candidate
    :return: boolean; True if candidate is in a checklist, False otherwise
    """

    sent_spans = get_sent_candidate_spans(c)
    sent = ''
    for span in sent_spans:
        words = span.get_parent()._asdict()['words']
        sent += ' '.join(words)

    pattern = '(¿\s*\S+\s*){2,}'

    b = regex_in_text(pattern, sent.encode('utf-8'))

    return True if b else False

def date_between(c):
    """
    Check whether a candidate has a date between its
    entities

    :param c: pain-anatomy candidate
    :return: boolean; True if candidate has a data between its entities, False otherwise
    """

    between_tokens = list(get_between_tokens(c))
    between_phrase = ' '.join(between_tokens) + ' '
    pattern = '[0-9]{2}/[0-9]{2}/[0-9]{4}'

    b = regex_in_text(pattern, between_phrase)

    return True if b else False

def misattached_entities(c):
    """
    Check whether a candidate pain-anatomy mention is mis-attached
    e.g. if note contains "chest pain, ache in abdomen" and
    candidate is (ache, chest)

    :param c: pain-anatomy candidate
    :return: boolean; True if candidate is misattached, False otherwise
    """

    between_tokens = list(get_between_tokens(c))

    return True if len(between_tokens) < 3 and ',' in between_tokens else False

def misattached_entities2(c):
    """
    Check whether a pain anatomy mention is mis-attached where pain mention precedes anatomy mention
    e.g. if note contains 'chest pain, left leg also tender'
    and candidate is (pain, left leg)

    :param c: pain-anatomy candidate
    :return: boolean; True if candidate is misattached, False otherwise
    """

    between_tokens = list(get_between_tokens(c))
    right_window = get_right_tokens(c, 14)
    flag = False
    return True if c.pain.char_end < c.anatomy.char_start and ',' in between_tokens and list_contains_pain_mention(right_window) else False

def misattached_entities3(c):
    """
    Check whether a pain anatomy mention is mis-attached where anatomy precedes pain mention and
    e.g. note contains 'dorsum of the foot, positive tenderness to the right toes' and candidate
    is (tenderness, dorsum of the foot)

    :param c: pain-anatomy candidate
    :return: boolean; True if candidate is misattached, False otherwise
    """

    between_tokens = list(get_between_tokens(c))
    right_window = get_right_tokens(c, 14)

    return True if c.anatomy.char_end < c.pain.char_start and ',' in between_tokens and list_contains_anatomy_mention(right_window) and not list_contains_anatomy_mention(between_tokens) else False

def left_pain_multiple_anatomy(c):
    """
    Check if pain entity that is not attached directly to an anatomical entity e.g. 'leg pain close to the right upper thigh'
    where candidate is (pain, upper right thigh)
    is attached to another entity to its left.

    :param c: pain-anatomy candidate
    :return: boolean; True if pain entity is attached to multiple anatomy entities, False otherwise
    """

    left_window = get_left_tokens(c, 5)

    return True if list_contains_anatomy_mention(left_window) and c.pain.char_end < c.anatomy.char_start else False

def LF_far_apart(c):
    """
    Check if entities in pain anatomy candidate are very far apart
    as defined in far_apart()

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    v = far_apart(c)

    return -1 if v else 0

def LF_less_far_apart(c):

    """
    Check if entities in pain anatomy are somewhat far apart
    as defined in less_far_apart()

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """
    v = less_far_apart(c)

    return -1 if v else 0

def LF_contiguous_right_pain(c):
    """
    Check for pain-anatomy candidates that are compound mentions
    e.g 'hip pain', 'leg pain'
    where pain mention is directly attached to anatomy mention
    and where the mention is not negated (using Negex)

    :param c: pain-anatomy candidate
    :return: 1 if True, 0 otherwise
    """

    possible_terms = [x['term'].split(' ') for x in negex.dictionary['definite'] if x['direction'] == 'forward']
    longest = len(max(possible_terms, key=len))
    window = longest + 2
    distance = len(list(get_between_tokens(c)))

    v = distance < 1
    v &= c.pain.char_end > c.anatomy.char_end
    v &= not negex.is_negated(c.pain, 'definite', 'left', window)

    return 1 if v else 0

def LF_near_contiguous_right_pain(c):
    """
    Check for pain anatomy-mentions that are close to contiguous e.g.
    'hip and knee pain' where candidate is (pain, hip)

    :param c: pain-anatomy candidate
    :return: 1 if True, 0 otherwise
    """

    possible_terms = [x['term'].split(' ') for x in negex.dictionary['definite'] if x['direction'] == 'forward']
    longest = len(max(possible_terms, key=len))
    left_window_length = longest + 2
    left_window = get_left_tokens(c, window=left_window_length)
    between_tokens = list(get_between_tokens(c))

    f = (lambda w: w.lower())
    between_terms = [ngram for ngram in tokens_to_ngrams(
        map(f, c.pain.get_parent()._asdict()['words'][c.anatomy.get_word_start():c.pain.get_word_start() + 1]),
        n_max=1)]
    between_phrase = ' '.join(between_terms) + ' '

    negated_in_between = False

    for pt in possible_terms:
        pattern = '\s'.join(pt) + '[-\s]*'
        negated_in_text = regex_in_text(pattern, between_phrase)
        if negated_in_text:
            negated_in_between = True

    odd_list = ["flexion", "regimen", "raise"]
    odd = False
    for oe in odd_list:
        if oe in between_phrase:
            odd = True

    pain_between = False
    for nterm in dict_pain:
        if nterm in between_tokens or nterm in left_window:
            pain_between = True

    v = len(between_tokens) < 10
    v &= ',' in between_tokens or 'and' in between_tokens
    v &= c.pain.char_start > c.anatomy.char_end
    v &= not negex.is_negated(c.anatomy, 'definite', 'left', left_window_length)
    v &= not negated_in_between
    v &= not pain_between
    v &= not candidate_in_list(c)
    v &= not misattached_entities(c)
    v &= not misattached_entities3(c)
    v &= not odd

    return 1 if v else 0


def LF_contiguous_left_pain(c):
    """
    Check for pain-anatomy candidates that are compound mentions
    e.g 'pain hip'
    where pain mention is directly attached to anatomy mention
    and where the mention is not negated (using Negex)

    :param c: pain-anatomy candidate
    :return: 1 if True, 0 otherwise
    """

    v = len(list(get_between_tokens(c))) < 1
    v &= c.pain.char_end < c.anatomy.char_end

    return 1 if v else 0


def LF_near_contiguous_left_pain(c):
    """
    Check for pain-anatomy candidates that are
    non-contiguous but close mentions,
    e.g., 'pain in the hip', 'tenderness of the right side'

    :param c: pain-anatomy candidate
    :return: 1 if True, 0 otherwise
    """

    between_tokens = list(get_between_tokens(c))

    left_window_length = 8
    negated = negex.is_negated(c, 'definite', 'left', left_window_length)

    right_window = get_right_tokens(c, window=3)

    pain_in_right_window = list_contains_pain_mention(right_window)

    v = len(between_tokens) < 3
    v &= c.pain.char_end < c.anatomy.char_start
    v &= not pain_in_right_window
    v &= not negated
    v &= not '(' in between_tokens
    v &= not ',' in between_tokens

    return 1 if v else 0

def LF_long_distance_left_pain(c):
    """
    Check for pain-anatomy candidates that are
    long distance mentions,
    e.g., 'pain in the lower right hip and left ankle'
    where candidate is (pain, left ankle)

    :param c: pain-anatomy candidate
    :return: 1 if True, 0 otherwise
    """

    between_tokens = list(get_between_tokens(c))
    right_window = get_right_tokens(c, 3)
    left_window_length = 5
    left_window = get_left_tokens(c, left_window_length)

    v = len(between_tokens) < 10
    v &= c.pain.char_end < c.anatomy.char_start
    v &= not list_contains_pain_mention(right_window)
    v &= not list_contains_pain_mention(between_tokens)
    v &= not list_contains_anatomy_mention(left_window)
    v &= not negex.is_negated(c, 'definite', 'left', left_window_length)
    v &= not date_between(c)
    v &= not candidate_in_list(c)
    v &= not left_pain_multiple_anatomy(c)

    return 1 if v else 0

def LF_complains_of(c):
    """
    Check if candidate is preceded by 'complains of' or some similar variant
    and is not negated (using Negex)

    :param c: pain-anatomy candidate
    :return: 1 if preceded by non-negated 'complains of' variant, -1 if preceded by negated 'complains of' variant, 0 otherwise
    """

    left_window = get_left_tokens(c, window=7)
    left_window_phrase = ' '.join(left_window)

    between_tokens = list(get_between_tokens(c))
    pattern = 'complain(s*|ing*)\sof'

    left_window_length = 7

    negated = negex.is_negated(c.pain, 'definite', 'left', left_window_length)

    v = len(between_tokens) <= 10
    v &= regex_in_text(pattern, left_window_phrase)

    v &= not negated

    v2 = regex_in_text(pattern, left_window_phrase)

    v2 &= negated

    if v:
        return 1
    elif v2:
        return -1
    else:
        return 0

def LF_pain_between_entities(c):
    """
    Check if there is a pain mention between entities in a
    candidate pain-anatomy mention

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    between_tokens = list(get_between_tokens(c))

    v = len(between_tokens) < 10
    v &= c.pain.char_start > c.anatomy.char_end
    v &= ',' in between_tokens
    v &= not '(' in between_tokens
    v &= not';' in between_tokens
    v &= list_contains_pain_mention(between_tokens)

    return -1 if v else 0

def LF_negex_definite_negation_left(c):
    """
    Check if candidate is preceded by definite negative mentions to the left
    of the candidate e.g. 'patient denies chest pain'
    (Using Negex)

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    possible_terms = [x['term'].split(' ') for x in negex.dictionary['definite'] if x['direction'] == 'forward']
    longest = len(max(possible_terms, key=len))
    left_window_length = longest + 2

    v = negex.is_negated(c, 'definite', 'left', left_window_length)

    return -1 if v else 0

def LF_negex_definite_negation_right(c):
    """
    Check if candidate is preceded by definite negative mentions to the right
    of the candidate e.g. 'chest pain is denied'
    (Using Negex)

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    possible_terms = [x['term'].split(' ') for x in negex_lexicon if
                      x['category'] == 'definite' and x['direction'] == 'backward']
    longest = len(max(possible_terms, key=len))
    right_window_length=longest + 2

    v = negex.is_negated(c, 'definite', 'right', right_window_length)

    return -1 if v else 0

def LF_candidate_in_list(c):
    """
    Check if a candidate is in a list

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """
    v = candidate_in_list(c)
    return -1 if v else 0

def LF_candidate_in_checklist(c):
    """
    Check if candidate is in a check list

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    v = candidate_in_checklist(c)
    return -1 if v else 0

def LF_misattached_entities(c):
    """
    Check if entities in pain-anatomy candidate are mis-attached as in
    misattached_entities()

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    v = misattached_entities(c)
    return -1 if v else 0

def LF_misattached_entities2(c):
    """
    Check if entities in pain-anatomy candidate are mis-attached as in
    misattached_entities2()

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    v = misattached_entities2(c)

    return -1 if v else 0

def LF_misattached_entities3(c):
    """
    Check if entities in pain-anatomy candidate are mis-attached as in
    misattached_entities3()

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """
    v = misattached_entities3(c)

    return -1 if v else 0

def LF_negated_term_between_entities(c):
    """
    Check if there is a negated term between entities in a pain-anatomy candidate

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    possible_terms = [x['term'].split(' ') for x in negex.dictionary['definite']]
    between_tokens = list(get_between_tokens(c))
    between_phrase = ' '.join(between_tokens)

    negated_between = False
    for pt in possible_terms:
        pattern = '\s'.join(pt) + '\s'
        pattern_in_text = regex_in_text(pattern, between_phrase)

        if pattern_in_text:
            negated_between = True

    v = negated_between
    return -1 if v else 0

def LF_pain_score_location(c):
    """
    Check if the term 'location :'
    appears between entities in pain-anatomy candidate
    and there is not an anatomy term between them

    :param c: pain-anatomy candidate
    :return: 1 if True, 0 otherwise
    """

    between_tokens = list(get_between_tokens(c))
    between_phrase = ' '.join(between_tokens)

    v = 'location :' in between_phrase
    v &= not text_contains_anatomy_mention(between_phrase)

    return 1 if v else 0

def LF_warning_signs_hypothetical(c):
    """
    Check if candidate is in a list of warning signs e.g.
    preceded by 'Warning Signs:'

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    sent_spans = get_sent_candidate_spans(c)
    sent = ''
    for span in sent_spans:
        words = span.get_parent()._asdict()['words']
        sent += ' '.join(words)

    v = 'warning signs :' in sent.lower()

    return -1 if v else 0

def LF_left_pain_multiple_anat(c):
    """
    Check if pain mention in candidate is attached to another anatomical entity

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    v = left_pain_multiple_anatomy(c)

    return -1 if v else 0

def LF_left_pain_anatomy_between(c):
    """
    Check if there is another anatomy mention between entities in a
    pain-anatomy candidate

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    between_tokens = list(get_between_tokens(c))

    v = c.pain.char_end < c.anatomy.char_start
    v &= list_contains_anatomy_mention(between_tokens)
    v &= not "radiates" in between_tokens
    v &= not ',' in between_tokens
    v &= not 'and' in between_tokens

    return -1 if v else 0

def LF_date_between(c):
    """
    Check if there is a date between entities in a
    pain-anatomy candidate

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    v = date_between(c)
    return -1 if v else 0

def LF_history_of_present_illness(c):
    """
    Check if candidate is in a HISTORY OF PRESENT ILLNESS section

    :param c: pain-anatomy candidate
    :return: 1 if True, 0 otherwise
    """

    left_window = get_left_tokens(c, window=100)
    sent_spans = get_sent_candidate_spans(c)
    sent = ''
    for span in sent_spans:
        words = span.get_parent()._asdict()['words']
        sent += ' '.join(words)

    left_window_phrase = ' '.join(left_window)

    pattern = 'history\sof\spresent\sillness'

    v = regex_in_text(pattern, left_window_phrase)
    v &= not less_far_apart(c)
    v &= not left_pain_multiple_anatomy(c)

    return 1 if v else 0

def LF_past_medical_history(c):
    """
    Check if candidate is in a past medical history section

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    left_window = get_left_tokens(c, window=100)
    left_window_phrase = ' '.join(left_window)

    pattern = 'past\smedical\shistory'

    v = regex_in_text(pattern, left_window_phrase)

    return -1 if v else 0

def LF_radiograph_view(c):
    """
    Check if the term view occurs between the pain and anatomy mentions
    in a candidate

    :param c: pain-anatomy candidate
    :return: -1 if True, 0 otherwise
    """

    between_tokens = list(get_between_tokens(c))
    between_phrase = ' '.join(between_tokens)

    v = 'view' in between_phrase

    return -1 if v else 0