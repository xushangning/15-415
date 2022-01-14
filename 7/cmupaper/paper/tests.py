"""Design Choices:
1. No test for `reset_db`. The code of `reset_db` is handed down as a definition
for database schema that shouldn't be change. What's the point of testing
something that can't fail, because it itself is the definition of correctness?
"""
from django.test import TestCase
from django.conf import settings
import psycopg

from paper import functions, models


class DbApiTestCase(TestCase):
    _conn = None

    @classmethod
    def setUpTestData(cls):
        cls._conn = psycopg.connect('dbname=' + settings.DATABASES['default']['NAME'])
        functions.reset_db(cls._conn)

    @classmethod
    def tearDownClass(cls):
        # Close the connection so that the test database can be deleted.
        cls._conn.close()

    def test_signing_up(self):
        test_user_name = 'andy'
        test_password = 'pavlo'
        self.assertEqual(functions.signup(self._conn, test_user_name, test_password)[0], 0)
        self.assertEqual(
            models.Users.objects.filter(username=test_user_name, password=test_password).count(),
            1
        )
