"""Design Choices:
1. No test for `reset_db`. The code of `reset_db` is handed down as a definition
for database schema that shouldn't be change. What's the point of testing
something that can't fail, because it itself is the definition of correctness?
"""
from django.test import TestCase
from django.conf import settings
import psycopg

from paper import functions


class DbApiTestCase(TestCase):

    def setUp(self):
        self.conn = psycopg.connect('dbname=' + settings.DATABASES['default']['NAME'])
        functions.reset_db(self.conn)

    def tearDown(self):
        functions.reset_db(self.conn)
        del self.conn

    def test_signing_up(self):
        self.assertEqual(functions.signup(self.conn, 'andy', 'pavlo')[0], 0)
