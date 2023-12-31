import unittest

from unittest.mock import patch
from mud_parser import MudParser, Phrase
from mud_parser.verb import VerbResponse
from data.models import MudObject, Room, Character
from exceptions import BadArguments

MUDOBJECT = MudObject(
    id=1,
    short_desc='A simple MudObject',
    long_desc='A not-so-simple MudObject',
    parent=1
)
CHARACTER = Character(
    id=2,
    short_desc='Novice TestCharacter',
    long_desc='a simple looking test character',
    name='TestCharacter',
    account_hash='abcdef12345'
)
ROOM_DESC = 'You are in the void.'
TARGET_DESC = 'a stinky green goblin'

MUD_OBJECTS = [MUDOBJECT, CHARACTER]

def mock_match_short_desc(x, y, z):
    """
    Mock - Finds objects where y is a substring of short_desc
    """
    return [object for object in MUD_OBJECTS if y in object.short_desc]

@patch.object(Room, 'match_short_desc', mock_match_short_desc)
@patch.object(Room, 'get_desc', lambda x, y: ROOM_DESC)
class TestMudParser(unittest.TestCase):
    def test_unknown_verb(self):
        """
        Test that garbage input returns a phrase error response
        """
        parse_return = MudParser.parse_data(None, CHARACTER, b'rawriamadinosaur').message_i
        self.assertTrue(isinstance(parse_return, bytes))
        self.assertTrue(parse_return.decode('utf-8') in MudParser.PHRASE_ERROR)

    def test_unknown_target(self):
        """
        Test that an unmatched target returns a target error response
        """
        parse_return = MudParser.parse_data(None, CHARACTER, b'look unknowncharacter').message_i
        self.assertTrue(parse_return.decode('utf-8') in MudParser.TARGET_ERROR)

    def test_target(self):
        """
        Test that a matched target returns the long_desc
        """
        parse_return = MudParser.parse_data(None, CHARACTER, b'look testcharacter').message_i
        self.assertTrue(parse_return, CHARACTER.long_desc)
        
@patch.object(Room, 'match_short_desc', lambda x, y, z: [MUDOBJECT])

class TestPhrase(unittest.TestCase):
    def test_action(self):
        """
        Test verb and noun phrase
        """
        test_phrase = Phrase('kill slimy green goblin')
        self.assertEqual(test_phrase.verb, 'kill')
        self.assertEqual(test_phrase.noun_chunks[-1], 'slimy green goblin')

    def test_action_with_preposition(self):
        """
        Test verb, noun phrase, and joining preposition
        """
        test_phrase = Phrase('put big blue cracker in shiny gold chest')
        self.assertEqual(test_phrase.verb, 'put')
        self.assertEqual(test_phrase.noun_chunks[0], 'big blue cracker')
        self.assertEqual(test_phrase.ins[-1], 'in')
        self.assertEqual(test_phrase.noun_chunks[-1], 'shiny gold chest')

    def test_action_with_too_many_prepositions(self):
        """
        Test that we error if noun_chunks != ins + 1
        """
        with self.assertRaises(BadArguments):
            Phrase('kill slimy green goblin at')

    def test_action_without_preposition(self):
        """
        Test that we error without a preopositional modifier
        """
        with self.assertRaises(BadArguments):
            Phrase('put big blue cracker shiny gold chest')
        # we need our verb lookup for this to work

    def test_emote(self):
        """
        Test emote verb
        """
        test_phrase = Phrase('laugh')
        self.assertEqual(test_phrase.verb, 'laugh')

    def test_emote_with_adverb(self):
        """
        Test emote verb, adverb modifier
        """
        test_phrase = Phrase('laugh maniacally')
        self.assertEqual(test_phrase.verb, 'laugh')
        self.assertEqual(test_phrase.descriptors[-1], 'maniacally')

    def test_emote_with_adjective(self):
        """
        Test emote verb, adjective modifier
        """
        test_phrase = Phrase('laugh maniac')
        self.assertEqual(test_phrase.verb, 'laugh')
        self.assertEqual(test_phrase.descriptors[-1], 'maniacally')

    def test_emote_with_two_modifiers(self):
        """
        Test emote with two modifiers
        """
        test_phrase = Phrase('laugh joyfully maniacally')
        self.assertEqual(test_phrase.verb, 'laugh')
        self.assertEqual(test_phrase.descriptors[-1], 'joyfully')

    def test_action_iteration(self):
        """
        Test iterator over an action phrase
        """
        mapping = {
            0: 'put',
            1: 'big blue cracker',
            2: 'in',
            3: 'shiny golden chest'
        }
        test_phrase = Phrase(' '.join(mapping.values()))

        for index, part_of_speech in enumerate(test_phrase):
            self.assertEqual(mapping[index], part_of_speech)

    def test_emote_iteration(self):
        """
        Test iterator over an emote phrase
        """
        mapping = {
            0: 'laugh',
            1: 'maniacally',
            2: 'at',
            3: 'George'
        }
        test_phrase = Phrase(' '.join(mapping.values()))

        for index, part_of_speech in enumerate(test_phrase):
            # we drop prepositions from emotes
            if index == 2:
                index = 3
            self.assertEqual(mapping[index], part_of_speech)
