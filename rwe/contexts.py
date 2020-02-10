from typing import Tuple, List, Dict


class Document(object):

    def __init__(self,
                 name: str,
                 sentences: List['Sentence']) -> None:
        self.name = name
        self.sentences = sentences
        for s in sentences:
            s.document = self
        self.annotations = {i: {} for i in range(len(sentences))}
        self.props = {}

    @property
    def text(self) -> str:
        t = ""
        for s in self.sentences:
            if len(t) != s.abs_char_offsets[0]:
                t += ' ' * (s.abs_char_offsets[0] - len(t))
            t += s.text
        return t

    def __repr__(self) -> str:
        return "Document({})".format(self.name)


class Sentence(object):

    def __init__(self, **kwargs) -> None:
        self.document = None
        self.__dict__.update(kwargs)

    @property
    def text(self) -> str:
        txt = ""
        offset = self.abs_char_offsets[0]
        for i, w in enumerate(self.words):
            if len(txt) != self.abs_char_offsets[i] - offset:
                txt += ' ' * (self.abs_char_offsets[i] - offset - len(txt))
            txt += w
        return txt

    @property
    def position(self) -> int:
        return self.i

    @property
    def char_offsets(self) -> List[int]:
        offset = self.abs_char_offsets[0]
        return [i - offset for i in self.abs_char_offsets]

    def __repr__(self) -> str:
        max_len = 25
        s = self.text.strip().replace("\n", " ")
        s = s if len(s) < max_len else s[0:max_len] + '...'
        return f"Sentence({s})"


class Span(object):

    def __init__(self,
                 char_start: int,
                 char_end: int,
                 sentence: Sentence,
                 attrib: str = 'words'):
        self.sentence   = sentence
        self.char_start = char_start
        self.char_end   = char_end
        self.attrib     = attrib
        self.props      = {}
        self.normalized = None

    def __hash__(self):
        v = (self.sentence.document.name, self.char_start, self.char_end)
        return hash(v)

    @property
    def abs_char_start(self):
        return self.char_start + self.sentence.abs_char_offsets[0]

    @property
    def abs_char_end(self):
        return self.abs_char_start + (self.char_end - self.char_start)
    
    @property
    def text(self):
        return self.sentence.text[self.char_start:self.char_end + 1]

    def get_word_start(self):
        return self.char_to_word_index(self.char_start)

    def get_word_end(self):
        return self.char_to_word_index(self.char_end)

    def get_n(self):
        return self.get_word_end() - self.get_word_start() + 1

    def char_to_word_index(self, ci):
        """Given a character-level index (offset), return the index of the **word this char is in**"""
        i = None
        for i, co in enumerate(self.sentence.char_offsets):
            if ci == co:
                return i
            elif ci < co:
                return i-1
        return i

    def word_to_char_index(self, wi):
        """Given a word-level index, return the character-level index (offset) of the word's start"""
        return self.sentence.char_offsets[wi]

    def get_attrib_tokens(self, a):
        return self.sentence.__getattribute__(a)[self.get_word_start():self.get_word_end() + 1]
    
    def __repr__(self):
        return "Span({})".format(self.text.replace("\n"," "))
     
    def get_attrib_span(self, a, sep=" "):
        """Get the span of sentence attribute _a_ over the range defined by word_offset, n"""
        # NOTE: Special behavior for words currently (due to correspondence with char_offsets)
        if a == 'words':
            return self.sentence.text[self.char_start:self.char_end + 1]
        else:
            return sep.join(self.get_attrib_tokens(a))

    def get_span(self, sep=" "):
        return self.get_attrib_span('words', sep)

    def __contains__(self, other_span):
        return other_span.char_start >= self.char_start and \
               other_span.char_end <= self.char_end


class Relation(object):

    def __init__(self,
                 type_name:str,
                 args: Dict[str, Span]) -> None:
        self.type_name = type_name
        self.args = args
        self.__dict__.update(args)

    def __iter__(self):
        for span in self.args.values():
            yield span

    def __getitem__(self, item):
        return list(self.args.values())[item]

    def __repr__(self):
        strs = [span.__repr__() for span in self.args.values()]
        return f"Relation[{self.type_name}]({','.join(strs)})"

    def __eq__(self, other):
        hashes = {name:span.__hash__() for name,span in self.args.items()}
        other = {name:span.__hash__() for name,span in other.args.items()}
        return hashes == other

    def __hash__(self):
        return hash(sum([s.__hash__() for s in self.args.values()]))

    @property
    def sentence(self):
        """We assume spans all live in the same sentence"""
        return self.__dict__[self.arg_names[0]].sentence



class Annotation(object):

    def __init__(self, doc_name: str,
                 span: Tuple[Tuple[int,int], ...],
                 etype: str,
                 text: str = None,
                 cid: str = None) -> None:
        """

        :param doc_name:
        :param span:
        :param etype:
        :param text:
        :param cid:
        """
        # Just use first token for abs offsets
        self.abs_char_start = span[0][0]
        self.abs_char_end = span[0][-1]

        self.doc_name = doc_name
        self.span = span
        self.text = text
        self.etype = etype
        self.cid = cid
        
    def __repr__(self):
        text = self.text.replace('\n',' ') + '|' if self.text else ''
        if len(self.span) == 1:
            return f"Annotation[{self.etype}]({text}{self.abs_char_start}-{self.abs_char_end})"
        else:
            return f"Annotation[{self.etype}]({text}{self.abs_char_start}...{self.abs_char_end})"

    @property
    def type(self):
        return self.etype

    def __hash__(self):
        return hash((self.etype, self.doc_name, self.span))

    def __eq__(self, other):
        return False if not isinstance(other, type(self)) else True
