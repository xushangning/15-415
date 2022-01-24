from typing import Optional, Any

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
    _conn: Optional[psycopg.Connection[tuple[Any, ...]]] = None
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

    def test_statistics(self):
        self._uploader.save()

        # Test APIs on an (almost) empty database.
        return_status, returned_papers = functions.get_timeline(self._conn, self._uploader.username)
        self.assertEqual(return_status, 0)
        self.assertEqual(len(returned_papers), 0)
        return_status, returned_papers = functions.get_timeline_all(self._conn)
        self.assertEqual(return_status, 0)
        self.assertEqual(len(returned_papers), 0)

        return_status, returned_papers = functions.get_papers_by_keyword(self._conn, '4')
        self.assertEqual(return_status, 0)
        self.assertEqual(len(returned_papers), 0)

        papers = tuple(map(
            lambda i: models.Paper.objects.create(
                title=str(i),
                username=self._uploader,
                begin_time=timezone.now()
            ),
            range(4)
        ))
        papers[0].description = '1 2 3 4 5 6 7 8 9'
        papers[0].save()
        papers[1].data = '1 2 3 4 5 6 7 8 9'
        papers[1].save()

        # No likes.
        return_status, likes = functions.get_likes(self._conn, papers[0].pid)
        self.assertEqual(return_status, 0)
        self.assertEqual(likes, 0)

        # The following users, papers and like relationships are recreated from
        # Figure 1 in Homework 7.
        alice = models.User.objects.create(username='alice', password='alice')
        bob = models.User.objects.create(username='bob', password='bob')
        cindy = models.User.objects.create(username='cindy', password='cindy')
        eve = models.User.objects.create(username='eve', password='eve')

        models.Like.objects.create(pid=papers[0], username=alice, like_time=timezone.now())
        models.Like.objects.create(pid=papers[0], username=bob, like_time=timezone.now())
        # We will call get_most_popular_papers with
        # begin_time=most_popular_paper_time.
        most_popular_paper_time = timezone.now()
        models.Like.objects.create(pid=papers[0], username=eve, like_time=timezone.now())
        models.Like.objects.create(pid=papers[1], username=bob, like_time=timezone.now())
        models.Like.objects.create(pid=papers[1], username=eve, like_time=timezone.now())
        models.Like.objects.create(pid=papers[2], username=cindy, like_time=timezone.now())
        models.Like.objects.create(pid=papers[3], username=cindy, like_time=timezone.now())
        models.Like.objects.create(pid=papers[3], username=eve, like_time=timezone.now())

        return_status, likes = functions.get_likes(self._conn, papers[0].pid)
        self.assertEqual(return_status, 0)
        self.assertEqual(likes, 3)

        return_status, returned_papers = functions.get_timeline(
            self._conn,
            self._uploader.username,
            count=3
        )
        self.assertEqual(return_status, 0)
        # Check papers are returned in chronological order (most recent first).
        self.assertTrue(all(
            paper[2] == title
            for paper, title in zip(returned_papers, (p.title for p in reversed(papers[-3:])))
        ))

        return_status, returned_papers = functions.get_timeline_all(self._conn, count=2)
        self.assertEqual(return_status, 0)
        self.assertEqual(returned_papers[0][2], papers[3].title)
        self.assertEqual(returned_papers[1][2], papers[2].title)

        # A paper that nobody likes shouldn't be returned.
        self._paper.save()
        return_status, returned_papers = functions.get_most_popular_papers(
            self._conn,
            begin_time=most_popular_paper_time
        )
        self.assertEqual(return_status, 0)
        # Check papers are returned in descending order of the number of likes,
        # with ties broken by pid.
        self.assertTrue(all(
            paper[2] == str(i) for paper, i in zip(returned_papers, (3, 1, 2, 0))
        ))

        return_status, returned_papers = functions.get_recommend_papers(
            self._conn, alice.username
        )
        self.assertEqual(return_status, 0)
        self.assertEqual(returned_papers[0][2], papers[1].title)
        self.assertEqual(returned_papers[1][2], papers[3].title)

        tags = tuple(map(
            lambda i: models.TagName.objects.create(tagname=str(i)),
            range(3)
        ))
        return_status, returned_papers = functions.get_papers_by_tag(
            self._conn,
            tags[0].tagname
        )
        self.assertEqual(return_status, 0)
        self.assertEqual(len(returned_papers), 0)

        for paper in papers:
            models.Tag.objects.create(pid=paper, tagname=tags[0])
        models.Tag.objects.create(pid=papers[0], tagname=tags[1])
        models.Tag.objects.create(pid=papers[1], tagname=tags[1])
        models.Tag.objects.create(pid=papers[1], tagname=tags[2])

        return_status, returned_papers = functions.get_papers_by_tag(
            self._conn, tags[0].tagname, count=2
        )
        self.assertEqual(return_status, 0)
        self.assertTrue(all(
            paper[2] == title
            for paper, title in zip(returned_papers, (p.title for p in reversed(papers[-2:])))
        ))

        return_status, returned_papers = functions.get_papers_by_keyword(self._conn, '3')
        self.assertEqual(return_status, 0)
        self.assertEqual(returned_papers[0][2], papers[3].title)
        self.assertEqual(returned_papers[1][2], papers[1].title)
        self.assertEqual(returned_papers[2][2], papers[0].title)

        return_status, returned_papers = functions.get_papers_by_liked(
            self._conn, eve.username, count=2
        )
        self.assertEqual(return_status, 0)
        self.assertEqual(returned_papers[0][2], papers[3].title)
        self.assertEqual(returned_papers[1][2], papers[2].title)

        return_status, returned_users = functions.get_most_active_users(self._conn, count=10)
        self.assertEqual(return_status, 0)
        self.assertEqual(returned_users, [self._uploader.username])

        return_status, returned_tags = functions.get_most_popular_tags(self._conn, count=2)
        self.assertEqual(return_status, 0)
        self.assertEqual(returned_tags, [tags[0].tagname, tags[1].tagname])

        return_status, returned_tag_pairs = functions.get_most_popular_tag_pairs(
            self._conn, count=3
        )
        self.assertEqual(return_status, 0)
        self.assertEqual(returned_tag_pairs, [
            (tags[0].tagname, tags[1].tagname),
            (tags[0].tagname, tags[2].tagname),
            (tags[1].tagname, tags[2].tagname)
        ])

        return_status, count = functions.get_number_papers_user(self._conn, self._uploader.username)
        self.assertEqual(return_status, 0)
        self.assertEqual(count, len(papers))

        return_status, count = functions.get_number_liked_user(self._conn, cindy.username)
        self.assertEqual(return_status, 0)
        self.assertEqual(count, 2)

        return_status, count = functions.get_number_tags_user(self._conn, self._uploader.username)
        self.assertEqual(return_status, 0)
        self.assertEqual(count, 3)
