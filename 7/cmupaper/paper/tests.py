from typing import Optional

import psycopg
from django.test import TransactionTestCase
from django.conf import settings

from paper import functions, models


class DbApiTestCase(TransactionTestCase):
    """There is no test for `reset_db`. The code of `reset_db` is handed down as
    a definition for database schema that shouldn't be change. What's the point
    of testing something that can't fail, because it itself is the definition of
    correctness?
    """
    _conn: Optional[psycopg.Connection] = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._conn = psycopg.connect('dbname=' + settings.DATABASES['default']['NAME'])
        functions.reset_db(cls._conn)

    @classmethod
    def tearDownClass(cls):
        cls._conn.close()
        super().tearDownClass()

    def tearDown(self):
        self._conn.cursor().execute('TRUNCATE tags, tagnames, likes, papers, users')
        self._conn.commit()

    def test_signing_up(self):
        test_user_name = 'andy'
        test_password = 'pavlo'
        self.assertEqual(functions.signup(self._conn, test_user_name, test_password)[0], 0)
        self.assertEqual(
            models.User.objects.filter(username=test_user_name, password=test_password).count(),
            1
        )

        # Duplicate insertion.
        self.assertEqual(functions.signup(self._conn, test_user_name, test_password)[0], 1)
        self.assertEqual(
            models.User.objects.filter(username=test_user_name, password=test_password).count(),
            1
        )

        # Long username and password.
        test_user_name = 'a' * (models.User.USERNAME_MAX_LENGTH * 2)
        test_password = 'a' * (models.User.PASSWORD_MAX_LENGTH * 2)

        self.assertEqual(functions.signup(self._conn, test_user_name, test_password)[0], 2)
        self.assertEqual(
            models.User.objects.filter(username=test_user_name, password=test_password).count(),
            0
        )

    def test_login(self):
        test_user_name = 'andy'
        test_password = 'pavlo'
        models.User.objects.create(username=test_user_name, password=test_password)

        self.assertEqual(functions.login(self._conn, test_user_name, test_password)[0], 0)

        # Non-existent user.
        self.assertEqual(functions.login(self._conn, 'wrong username', test_password)[0], 1)
        # Wrong password.
        self.assertEqual(functions.login(self._conn, test_user_name, 'wrong password')[0], 2)

    def test_adding_new_paper(self):
        test_user_name = 'andy'
        test_password = 'pavlo'
        models.User.objects.create(username=test_user_name, password=test_password)
        # https://db.cs.cmu.edu/mmap-cidr2022/
        test_paper = {
            'title': 'Are You Sure You Want to Use MMAP in Your Database Management System?',
            'desc': 'MMAP‘s perceived ease of use has seduced database '
                    'management system (DBMS) developers for decades as a '
                    'viable alternative to implementing a buffer pool. There '
                    'are, however, severe correctness and performance issues '
                    'with MMAP that are not immediately apparent.',
            'text': 'An important feature of disk-based DBMSs is their ability '
                    'to support databases that are larger than the available '
                    'physical memory. This functionality allows a user to query '
                    'a database as if it resides entirely in memory, even if it '
                    'does not fit all at once. DBMSs achieve this illusion by '
                    'reading pages of data from secondary storage (e.g., HDD, '
                    'SSD) into memory on demand. If there is not enough memory '
                    'for a new page, the DBMS will evict an existing page that '
                    'is no longer needed in order to make room.',
            'tags': ('mmap', 'database', 'dbms', 'dbms implementation')
        }

        def assert_insertion_fail(ret: tuple[int, Optional[int]]):
            self.assertEqual(ret[0], 1)
            self.assertIsNone(ret[1])

        # Title and description too long.
        assert_insertion_fail(functions.add_new_paper(
            self._conn,
            test_user_name,
            **test_paper
        ))

        assert_insertion_fail(functions.add_new_paper(
            self._conn,
            test_user_name,
            'A Paper with a Very Long Tag',
            None,
            None,
            ('a' * (models.TagName.TAG_MAX_LENGTH * 2),)
        ))
        # Up until now, no papers were successfully added.
        self.assertEqual(models.Paper.objects.count(), 0)

        return_status, paper_id = functions.add_new_paper(
            self._conn,
            test_user_name,
            'A Paper with Only a Title',
            None,
            None,
            ()
        )
        self.assertEqual(return_status, 0)
        self.assertEqual(models.Paper.objects.filter(pid=paper_id).count(), 1)
        self.assertEqual(models.TagName.objects.count(), 0)
        self.assertEqual(models.Tag.objects.count(), 0)

        return_status, paper_id = functions.add_new_paper(
            self._conn,
            test_user_name,
            test_paper['title'][:models.Paper.TITLE_MAX_LENGTH],
            test_paper['desc'][:models.Paper.DESCRIPTION_MAX_LENGTH],
            test_paper['text'],
            test_paper['tags']
        )
        self.assertEqual(return_status, 0)
        self.assertEqual(models.Paper.objects.filter(pid=paper_id).count(), 1)
        for tag in models.TagName.objects.all():
            self.assertIn(tag.tagname, test_paper['tags'])
