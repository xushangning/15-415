"""Design Choices:
1. No test for `reset_db`. The code of `reset_db` is handed down as a definition
for database schema that shouldn't be change. What's the point of testing
something that can't fail, because it itself is the definition of correctness?
"""
from django.test import TransactionTestCase
from django import db

from paper import functions, models


class DbApiTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        functions.reset_db(db.connection)

    def tearDown(self):
        db.connection.cursor().execute('TRUNCATE tags, tagnames, likes, papers, users')

    def test_signing_up(self):
        test_user_name = 'andy'
        test_password = 'pavlo'
        self.assertEqual(functions.signup(db.connection, test_user_name, test_password)[0], 0)
        self.assertEqual(
            models.Users.objects.filter(username=test_user_name, password=test_password).count(),
            1
        )

        # Duplicate insertion.
        self.assertEqual(functions.signup(db.connection, test_user_name, test_password)[0], 1)
        self.assertEqual(
            models.Users.objects.filter(username=test_user_name, password=test_password).count(),
            1
        )

        # Long username and password.
        test_user_name = 'a' * (models.Users.USERNAME_MAX_LENGTH * 2)
        test_password = 'a' * (models.Users.PASSWORD_MAX_LENGTH * 2)

        self.assertEqual(functions.signup(db.connection, test_user_name, test_password)[0], 2)
        self.assertEqual(
            models.Users.objects.filter(username=test_user_name, password=test_password).count(),
            0
        )

    def test_login(self):
        test_user_name = 'andy'
        test_password = 'pavlo'
        models.Users.objects.create(username=test_user_name, password=test_password)

        self.assertEqual(functions.login(db.connection, test_user_name, test_password)[0], 0)

        # Non-existent user.
        self.assertEqual(functions.login(db.connection, 'wrong username', test_password)[0], 1)
        # Wrong password.
        self.assertEqual(functions.login(db.connection, test_user_name, 'wrong password')[0], 2)
