from typing import Optional

import psycopg
from django.test import TransactionTestCase
from django.conf import settings
from django.utils import timezone

from paper import functions, models


class DbApiTestCase(TransactionTestCase):
    """There is no test for `reset_db`. The code of `reset_db` is handed down as
    a definition for database schema that shouldn't be change. What's the point
    of testing something that can't fail, because it itself is the definition of
    correctness?
    """
    _conn: Optional[psycopg.Connection] = None
    _uploader: Optional[models.User] = None
    _paper: Optional[models.Paper] = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._conn = psycopg.connect('dbname=' + settings.DATABASES['default']['NAME'])
        functions.reset_db(cls._conn)

        cls._uploader = models.User(username='uploader', password='uploader')
        cls._paper = models.Paper(
            title='A Very Versatile Paper for Testing',
            username=cls._uploader,
            description='This paper is for testing purposes only.',
            data='This is the data for the paper.',
            begin_time=timezone.now()

        )

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

    def test_deleting_paper(self):
        # Delete a paper that doesn't exist.
        self.assertEqual(functions.delete_paper(self._conn, 100)[0], 1)

        test_paper = models.Paper.objects.create(
            title='A Paper',
            username=models.User.objects.create(username='uploader', password='uploader'),
            begin_time=timezone.now()
        )
        test_tag = models.TagName.objects.create(tagname='tag')
        models.Tag.objects.create(pid=test_paper, tagname=test_tag)
        models.Like.objects.create(
            pid=test_paper,
            username=models.User.objects.create(
                username='user_who_likes_paper',
                password='another_user'
            ),
            like_time=timezone.now()
        )
        self.assertEqual(functions.delete_paper(self._conn, test_paper.pid)[0], 0)
        # Check cascade deletion.
        self.assertEqual(models.Tag.objects.count(), 0)
        self.assertEqual(models.Like.objects.count(), 0)

    def test_getting_paper_tags(self):
        # Non-existent paper.
        self.assertEqual(functions.get_paper_tags(self._conn, 100)[0], 1)

        test_paper = models.Paper.objects.create(
            title='A Paper with So Many Tags',
            username=models.User.objects.create(username='uploader', password='uploader'),
            begin_time=timezone.now()
        )
        # First no tags.
        return_status, tags = functions.get_paper_tags(self._conn, test_paper.pid)
        self.assertEqual(return_status, 0)
        self.assertEqual(len(tags), 0)

        tags = [str(i) for i in range(20)]
        for tag in tags:
            models.Tag.objects.create(
                pid=test_paper,
                tagname=models.TagName.objects.create(tagname=tag)
            )
        return_status, returned_tags = functions.get_paper_tags(self._conn, test_paper.pid)
        self.assertEqual(return_status, 0)
        # Returned tags should be sorted in lexicographical order.
        tags.sort()
        self.assertTrue(tags == returned_tags)

    def test_liking_paper(self):
        self._uploader.save()
        self._paper.save()
        # The uploader can't like their own paper.
        self.assertEqual(functions.like_paper(self._conn, self._uploader.username, self._paper.pid)[0], 1)
        self.assertEqual(models.Like.objects.count(), 0)

        liker = models.User.objects.create(username='liker', password='liker')
        self.assertEqual(functions.like_paper(self._conn, liker.username, self._paper.pid)[0], 0)
        # One can't like a paper twice.
        self.assertEqual(functions.like_paper(self._conn, liker.username, self._paper.pid)[0], 1)
        self.assertEqual(models.Like.objects.count(), 1)

    def test_unliking_paper(self):
        self._uploader.save()
        self._paper.save()
        liker = models.User.objects.create(username='liker', password='liker')

        # You can only unlike a liked paper.
        self.assertEqual(functions.unlike_paper(self._conn, liker.username, self._paper.pid)[0], 1)

        models.Like.objects.create(pid=self._paper, username=liker, like_time=timezone.now())
        self.assertEqual(functions.unlike_paper(self._conn, liker.username, self._paper.pid)[0], 0)
        self.assertEqual(models.Like.objects.count(), 0)

    def test_getting_likes(self):
        self._uploader.save()
        test_paper = models.Paper.objects.create(
            title='1',
            username=self._uploader,
            begin_time=timezone.now()
        )

        # No likes.
        return_status, likes = functions.get_likes(self._conn, test_paper.pid)
        self.assertEqual(return_status, 0)
        self.assertEqual(likes, 0)

        alice = models.User.objects.create(username='alice', password='alice')
        bob = models.User.objects.create(username='bob', password='bob')
        models.Like.objects.create(pid=test_paper, username=alice, like_time=timezone.now())
        models.Like.objects.create(pid=test_paper, username=bob, like_time=timezone.now())
        return_status, likes = functions.get_likes(self._conn, test_paper.pid)
        self.assertEqual(return_status, 0)
        self.assertEqual(likes, 2)
