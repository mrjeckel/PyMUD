import logging
import random
import spacy
import copy

from typing import List, Tuple, Union
from sqlalchemy.orm.session import Session
from exceptions import (UnknownVerb,
                        BadArguments,
                        UnknownVerb,
                        UnknownTarget)
from mud_parser.verb import VerbResponse, Emote, ACTION_DICT, EMOTE_DICT

from data.models import Character

NLP = spacy.load("en_core_web_sm")

class Phrase:
    """
    Transforms a client string into an actionable object
    """
    EXCLUDE_FROM_NOUN_CHUNKS = ['DET', 'ADV']

    def __init__(self, phrase: str):
        self.is_emote = False
        self.is_action = False
        self.verb, self.ins, self.noun_chunks, self.descriptors = self._parse(phrase)

    def _parse(self, phrase: str) -> Tuple[str, List[str], List[str]]:
        """
        Parse parts of speech from a string phrase - skip articles
        """
        doc = NLP(phrase)
        verb = doc[0].text

        ins = [token.text for token in doc[1:] if token.pos_ == 'ADP']
        descriptors = []
        noun_chunks = self._build_noun_chunks(doc)

        if verb in ACTION_DICT.keys():
            self.is_action = True
            ACTION_DICT[verb].validate_phrase_structure(ins, noun_chunks)
        elif verb in EMOTE_DICT.keys():
            self.is_emote = True
            descriptors = [Emote.complete_adverb(doc[1].text)] if len(doc) > 1 else []
            Emote.validate_phrase_structure(noun_chunks, descriptors)
        else:
            raise UnknownVerb
            
        return verb, ins, noun_chunks, descriptors
    
    def _build_noun_chunks(self, doc: spacy.tokens.doc.Doc) -> List[str]:
        """
        Construct noun phrases with adjectives and nouns
        """
        stripped_phrase = [token for token in doc[1:] if
                           token.pos_ not in self.EXCLUDE_FROM_NOUN_CHUNKS]
        noun_chunks = []
        local_chunk  = ''
        for token in stripped_phrase:
            if token.pos_ == 'ADP':
                if local_chunk:
                    noun_chunks.append(local_chunk.strip())
                    local_chunk = ''
            else:
                local_chunk = local_chunk + ' ' + token.text
        if local_chunk:
            noun_chunks.append(local_chunk.strip())
        return noun_chunks

    def __iter__(self):
        """
        Builds a list with seperate parts of speech as elements
        """
        pos_list = [self.verb]

        if self.is_emote:
            pos_list.append(self.descriptors[0])
            pos_list.append(self.noun_chunks[0])
        elif self.is_action:
            for chunk_index, chunk in enumerate(self.noun_chunks):
                pos_list.append(chunk)
                try:
                    pos_list.append(self.ins[chunk_index])
                except IndexError:
                    pass        

        logging.debug(f'Phrase.__iter__: {pos_list}')
        self.pos_list = pos_list
        return self
    
    def __next__(self):
        try:
            return self.pos_list.pop(0)
        except IndexError:
            raise StopIteration

class MudParser:
    """
    Turn a client string into an executable command
    """
    NEWLINE = b'\r\n'
    PHRASE_ERROR = [
        'I\'m sorry, what?',
        'I don\'t understand what you want.',
        'Come again?',
        'Please try to be more coherent.'
    ]
    TARGET_ERROR = [
        'I couldn\'t find what you were referring to.',
        'That is not here.',
        'Do what to whom?'
    ]
    
    @classmethod
    def parse_data(cls, session: Session, character: Character, data: bytes):
        """
        Invoke a verb and format the response
        """
        try:
            input = data.decode('utf-8').strip().lower()
            if not input:
                return VerbResponse(b'', character_id=character.id)
            phrase = Phrase(input)
            if phrase.is_action:
                response = ACTION_DICT[phrase.verb].execute(session, character, phrase)
            elif phrase.is_emote:
                response = EMOTE_DICT[phrase.verb].execute(session, character, phrase)
            return response
        except UnknownVerb:
            logging.debug(f'Unable to parse data: {input} - {character.name}')
            return VerbResponse(message_i=random.choice(cls.PHRASE_ERROR),
                                character_id=character.id)
        except UnknownTarget:
            logging.debug(f'Unable to find target: {input} - {character.name}')
            return VerbResponse(message_i=random.choice(cls.TARGET_ERROR),
                                character_id=character.id)
        except BadArguments as e:
            return VerbResponse(message_i=str(e), character_id=character.id)
    
    @classmethod
    def format_newline(cls, message: bytes):
        newline_char = slice(len(message) - len(cls.NEWLINE), len(message))
        if message[newline_char] != cls.NEWLINE:
            return message + cls.NEWLINE
        return message
