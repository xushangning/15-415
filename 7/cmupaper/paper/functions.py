"""
Name:
AndrewID:
"""
from typing import Optional, Any
from collections.abc import Sequence

import psycopg2 as psy
import psycopg

from datetime import datetime
from pytz import timezone
from .constants import *

"""
General rules:
    (1) How will the WebApp call these APIs?
    Say we have an API foo(...) defined in this file. The upper layer Application
    will invoke these API through a wrapper in the following way:

    database_wrapper(...):
        conn = None
        try:
            conn = psycopg2.connection()
            res = foo(conn, ...)
            return res
        except psycopg2.DatabaseError, e:
            print "Error %s: " % e.argsp[0]
            conn.rollback()
            return DB_ERROR, None
        finally:
            if conn:
                conn.close()

    So, you don't need to care about the establishment and termination of
    the database connection, we will pass it as a parameter to the api.

    (2) General pattern for return value.
    Return value of every API defined here is a two element tuples (status, res).
    Status indicates whether the API call is success or not. Status = 0 means success,
    otherwise the web app will identify the error type by the value of the status.

    Res is the actual return value from the API. If the API has no return value, it should be
    set to None. Otherwise it could be any python data structures or primitives.
"""

Connection = psycopg.Connection[tuple[Any, ...]]
"""Type of psycopg.Connection we are using"""

Paper = tuple[int, str, str, datetime, str]


def example_select_current_time(conn):
    """
    Example: Get current timestamp from the database

    :param conn: A postgres database connection object
    :return: (status, retval)
        (0, dt)     Success, retval is a python datetime object
        (1, None)           Failure
    """
    try:
        # establish a cursor
        cur = conn.cursor()
        # execute a query
        cur.execute("SELECT localtimestamp")
        # get back result tuple
        res = cur.fetchone()
        # extract the result as a datetime object
        dt = res[0]
        # return the status and result
        return 0, dt
    except psy.DatabaseError as e:
        # catch any database exception and return failure status
        return 1, None


# Admin APIs


def reset_db(conn: Connection):
    """
    Reset the entire database.
    Delete all tables and then recreate them.

    :param conn: A postgres database connection object
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    commands = (
        """
        DROP TABLE IF EXISTS tags, tagnames, likes, papers, users
        """,
        """
        CREATE TABLE IF NOT EXISTS users(
            username VARCHAR(50) NOT NULL,
            password VARCHAR(32) NOT NULL,
            PRIMARY KEY(username)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS papers(
            pid  SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            title VARCHAR(50),
            begin_time TIMESTAMP NOT NULL,
            description VARCHAR(500),
            data TEXT,
            FOREIGN KEY(username) REFERENCES users ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX paper_text_idx ON papers USING gin(to_tsvector('english', data))
        """,
        """
        CREATE TABLE IF NOT EXISTS tagnames(
            tagname VARCHAR(50) NOT NULL,
            PRIMARY KEY(tagname)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS likes(
            pid INT NOT NULL,
            username VARCHAR(50) NOT NULL,
            like_time TIMESTAMP NOT NULL,
            PRIMARY KEY(pid, username),
            FOREIGN KEY(pid) REFERENCES papers ON DELETE CASCADE,
            FOREIGN KEY(username) REFERENCES users ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS tags(
            pid INT NOT NULL,
            tagname VARCHAR(50) NOT NULL,
            PRIMARY KEY(pid, tagname),
            FOREIGN KEY(pid) REFERENCES papers ON DELETE CASCADE,
            FOREIGN KEY(tagname) REFERENCES tagnames ON DELETE CASCADE
        );
        """,
    )
    cur = conn.cursor()
    for command in commands:
        cur.execute(command)
    conn.commit()
    return 0, None

# Basic APIs


def signup(conn: Connection, uname: str, pwd: str):
    """
    Register a user with a username and password.
    This function first check whether the username is used. If not, it
    registers the user in the users table.

    :param conn:  A postgres database connection object
    :param uname: A string of username
    :param pwd: A string of user's password
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure -- Username is used
        (2, None)   Failure -- Other errors
    """
    return_status = 2
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s) '
                       'ON CONFLICT (username) DO NOTHING', (uname, pwd))
        conn.commit()
        return_status = int(not cursor.rowcount)
    except Exception:
        conn.rollback()
    return return_status, None


def login(conn: Connection, uname: str, pwd: str):
    """
    Login if user and password match.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param pwd: A string of user's password
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure -- User does not exist
        (2, None)   Failure -- Password incorrect
        (3, None)   Failure -- Other errors
    """
    return_status = 3
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT password = %s FROM users WHERE username = %s', (pwd, uname))
        res = cursor.fetchall()
        if len(res) == 0:
            return_status = 1
        elif res[0][0]:
            return_status = 0
        else:
            return_status = 2
    except Exception:
        conn.rollback()

    return return_status, None

# Event related


def add_new_paper(conn: Connection, uname: str, title: str, desc: Optional[str],
                  text: Optional[str], tags: Sequence[str]) -> tuple[int, Optional[int]]:
    """
    Create a new paper with  tags.
    Note that this API should touch multiple tables.
    Make sure you define a transaction properly. Also, don't forget to set the begin_time
    of the paper as current time.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param title: A string of the title of the paper
    :param desc: A string of the description of the paper
    :param text: A string of the text content of the uploaded pdf file
    :param tags: A list of string, each element is a tag associate to the paper
    :return: (status, retval)
        (0, pid)    Success
                    Return the pid of the newly inserted paper in the res field of the return value
        (1, None)   Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO papers (username, title, begin_time, description, data) '
            'VALUES (%s, %s, %s, %s, %s) RETURNING pid',
            (uname, title, datetime.now(), desc, text)
        )
        paper_id = cursor.fetchone()[0]
        if len(tags):
            cursor.executemany(
                'INSERT INTO tagnames (tagname) VALUES (%s) ON CONFLICT DO NOTHING',
                ((tag,) for tag in tags)
            )
            cursor.executemany(
                'INSERT INTO tags (pid, tagname) VALUES (%s, %s)',
                ((paper_id, tag) for tag in tags)
            )
        conn.commit()
        return_status = 0
    except Exception:
        conn.rollback()
        paper_id = None
    return return_status, paper_id


def delete_paper(conn: Connection, pid: int) -> tuple[int, None]:
    """
    Delete a paper by the given pid.

    :param conn: A postgres database connection object
    :param pid: An int of pid
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM papers WHERE pid = %s', (pid,))
        conn.commit()
        return_status = int(cursor.rowcount != 1)
    except Exception:
        conn.rollback()
    return return_status, None


def get_paper_tags(conn: Connection, pid: int) -> tuple[int, Optional[list[str]]]:
    """
    Get all tags of a paper

    :param conn: A postgres database connection object
    :param pid: An int of pid
    :return: (status, retval)
        (0, [tag1, tag2, ...])      Success
                                    Return a list of string. Each string is a tag of the paper.
                                    Note that the list should be sorted in a lexical ascending order.
                                    Example:
                                            (0, ["database", "multi-versioned"])

        (1, None)                   Failure
    """
    try:
        return_status = 0
        cursor = conn.cursor()
        cursor.execute(
            'SELECT tagname FROM tags WHERE pid = %s ORDER BY tagname',
            (pid,)
        )
        tags = cursor.fetchall()
        if len(tags):
            tags = [tag[0] for tag in tags]
        else:
            # Check if the paper exists.
            cursor.execute('SELECT COUNT(*) FROM papers WHERE pid = %s', (pid,))
            if cursor.fetchone()[0] == 0:
                return_status = 1
                tags = None
        conn.commit()
    except Exception:
        conn.rollback()
        return_status = 1
        tags = None
    return return_status, tags

# Vote related


def like_paper(conn: Connection, uname: str, pid: int) -> tuple[int, None]:
    """
    Record a like for a paper. Timestamped the like with the current timestamp

    You need to ensure that (1) a user should not like his/her own paper, (2) a user can not like a paper twice.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param pid: An int of pid
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT username = %s FROM papers WHERE pid = %s', (uname, pid))
        if not cursor.fetchone()[0]:
            cursor.execute(
                'INSERT INTO likes (username, pid, like_time) VALUES (%s, %s, %s)',
                (uname, pid, datetime.now())
            )
            return_status = 0
        conn.commit()
    except Exception:
        conn.rollback()
        return_status = 1
    return return_status, None


def unlike_paper(conn: Connection, uname: str, pid: int) -> tuple[int, None]:
    """
    Record an unlike for a paper

    You need to ensure that the user calling unlike has liked the paper before

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param pid: An int of pid
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM likes WHERE username = %s AND pid = %s',
            (uname, pid)
        )
        conn.commit()
        return_status = int(cursor.rowcount != 1)
    except Exception:
        conn.rollback()
        return_status = 1
    return return_status, None


def get_likes(conn: Connection, pid: int) -> tuple[int, Optional[int]]:
    """
    Get the number of likes of a paper

    :param conn: A postgres database connection object
    :param pid: An int of pid
    :return: (status, retval)
        (0, like_count)     Success, retval should be an integer of like count
        (1, None)           Failure
    """
    return_status = 1
    like_count = None
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM likes WHERE pid = %s', (pid,))
        like_count = cursor.fetchone()[0]
        conn.commit()
        return_status = 0
    except Exception:
        conn.rollback()
    return return_status, like_count

# Search related


def get_timeline(conn: Connection, uname: str, count=10)\
        -> tuple[int, Optional[list[Paper, ...]]]:
    """
    Get timeline of a user.

    You should return $count most recent posts of a user. The result should be ordered first by time (newest first)
    and then break ties by pid (ascending).

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param count: An int indicating the maximum number of papers you can return
    :return: (status, retval)
        (0, [(pid, username, title, begin_time, description), (...), ...])
          Success, retval is a list of quintuple. Each element of the quintuple is of the following type:
            pid --  Integer
            username, title, description -- String
            begin_time  -- A datetime.datetime object
            For example, the return value could be:
            (
                0,
                [
                    (1, "Alice", "title", begin_time, "description")),
                    (2, "Alice", "title2", begin_time2, "description2"))
                ]
            )


        (1, None)
            Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT pid, username, title, begin_time, description FROM papers '
            'WHERE username = %s ORDER BY begin_time DESC, pid LIMIT %s',
            (uname, count)
        )
        papers = cursor.fetchall()
        conn.commit()
        return_status = 0
    except Exception:
        conn.rollback()
        papers = None
    return return_status, papers


def get_timeline_all(conn: Connection, count=10)\
        -> tuple[int, Optional[list[Paper, ...]]]:
    """
    Get at most $count recent papers

    The results should be ordered by begin_time (newest first). Break ties by pid.

    :param conn: A postgres database connection object
    :param count: An int indicating the maximum number of papers you can return
    :return: (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT pid, username, title, begin_time, description FROM papers '
            'ORDER BY begin_time DESC, pid LIMIT %s',
            (count,)
        )
        papers = cursor.fetchall()
        conn.commit()
        return_status = 0
    except Exception:
        conn.rollback()
        papers = None
    return return_status, papers


def get_most_popular_papers(conn: Connection, begin_time: datetime, count=10)\
        -> tuple[int, Optional[list[Paper, ...]]]:
    """
    Get at most $count papers posted after $begin_time according that have the most likes.

    You should order papers first by number of likes (descending) and break ties by pid (ascending).
    Also, paper with 0 like should not be listed here.

    :param conn: A postgres database connection object
    :param begin_time: A datetime.datetime object
    :param count:   An integer
    :return: (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT pid, username, title, begin_time, description FROM papers JOIN ('
            'SELECT pid, COUNT(*) AS like_count FROM likes '
            'WHERE pid IN (SELECT pid FROM papers WHERE begin_time > %s) GROUP BY pid'
            ') AS t USING (pid) ORDER BY like_count DESC, pid LIMIT %s',
            (begin_time, count)
        )
        papers = cursor.fetchall()
        conn.commit()
        return_status = 0
    except Exception:
        conn.rollback()
        papers = None
    return return_status, papers


def get_recommend_papers(conn: Connection, uname: str, count=10)\
        -> tuple[int, Optional[list[Paper, ...]]]:
    """
    Recommended at most $count papers for a user.

    Check T.15 in the project writeup for detailed description of this API.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param count:   An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            'WITH liked_papers AS (SELECT DISTINCT pid FROM likes WHERE username = %s), '
            'recommended_papers AS (SELECT pid, COUNT(*) AS like_count FROM likes '
            'WHERE username IN (SELECT DISTINCT username FROM likes WHERE pid IN (SELECT * FROM liked_papers)) '
            'AND pid NOT IN (SELECT * FROM liked_papers) '
            'GROUP BY pid) '
            'SELECT pid, username, title, begin_time, description FROM papers '
            'JOIN recommended_papers USING (pid) ORDER BY like_count DESC, pid LIMIT %s',
            (uname, count)
        )
        papers = cursor.fetchall()
        conn.commit()
        return_status = 0
    except Exception:
        conn.rollback()
        papers = None
    return return_status, papers


def get_papers_by_tag(conn, tag, count = 10):
    """
    Get at most $count papers that have the given tag

    The result should first be ordered by begin time (newest first). Break ties by pid (ascending).

    :param conn: A postgres database connection object
    :param tag: A string of tag
    :param count: An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    return 1, None


def get_papers_by_keyword(conn: Connection, keyword: str, count=10)\
        -> tuple[int, Optional[list[Paper, ...]]]:
    """
    Get at most $count papers that match a keyword in its title, description *or* text field

    The result should first be ordered by begin time (newest first). Break ties by pid (ascending).

    The GIN index on the data field is so stupid. Because the index is only on
    the data field, searches on title and description still require a full scan
    anyway, rendering the index useless. The correct approach is to create an
    index on concatenation of the three fields.

    :param conn: A postgres database connection object
    :param keyword: A string of keyword, e.g. "database"
    :param count: An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    return_status = 1
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pid, username, title, begin_time, description FROM papers "
            "WHERE title LIKE '%%' || %s || '%%' "
            "OR description LIKE '%%' || %s || '%%' "
            "OR to_tsquery('english', %s) @@ to_tsvector('english', data) "
            "ORDER BY begin_time DESC, pid LIMIT %s",
            (keyword, keyword, keyword, count)
        )
        papers = cursor.fetchall()
        conn.commit()
        return_status = 0
    except Exception:
        conn.rollback()
        papers = None
    return return_status, papers


def get_papers_by_liked(conn, uname, count = 10):
    """
    Get at most $count papers that liked by the given user.

    The result should first be ordered by the time the like is made (newest first). Break ties by pid (ascending).

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param count: An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    return 1, None


# Statistics related


def get_most_active_users(conn, count = 1):
    """
    Get at most $count users that post most papers.

    The result should first be ordered by number of papers posted by the user. Break ties by username (lexically
    ascending). User that never posted papers should not be listed.

    :param conn: A postgres database connection object
    :param count: An integer
    :return: (status, retval)
        (0, [uname1, uname2, ...])
            Success, retval is a list of username. Each element in the list is a string. Return empty list if no
            username found.
        (1, None)
            Failure
    """
    return 1, None


def get_most_popular_tags(conn, count = 1):
    """
    Get at most $count many tags that gets most used among all papers

    The result should first be ordered by number of papers that has the tags. Break ties by tag name (lexically
    ascending).

    :param conn: A postgres database connection object
    :param count: An integer
    :return:
        (0, [(tagname1, count1), (tagname2, count2), ...])
            Success, retval is a list of tagname. Each element is a pair where the first component is the tagname
            and the second one is its count
        (1, None)
            Failure
    """
    return 1, None


def get_most_popular_tag_pairs(conn, count = 1):
    """
    Get at most $count many tag pairs that have been used together.

    You should avoid duplicate pairs like (foo, bar) and (bar, foo). They should only be counted once with lexical
    order. Results should first be ordered by number occurrences in papers. Break ties by tag name (lexically
    ascending).

    :param conn: A postgres database connection object
    :param count: An integer
    :return:
        (0, [(tag11, tag12, count), (tag21, tag22, count), (...), ...])
            Success, retval is a list of three-tuples. The elements of the three-tuple are two strings and a count.

        (1, None)
            Failure
    """
    return 1, None


def get_number_papers_user(conn, uname):
    """
    Get the number of papers posted by a given user.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :return:
        (0, count)
            Success, retval is an integer indicating the number papers posted by the user
        (1, None)
            Failure
    """
    return 1, None


def get_number_liked_user(conn, uname):
    """
    Get the number of likes liked by the user

    :param conn: A postgres database connection object
    :param uname:   A string of username
    :return:
        (0, count)
            Success, retval is an integer indicating the number of likes liked by the user
        (1, None)
            Failure
    """
    return 1, None


def get_number_tags_user(conn, uname):
    """
    Get the number of distinct tagnames used by the user.

    Note that you need to eliminate the duplication.

    :param conn: A postgres database connection object
    :param uname:  A string of username
    :return:
        (0, count)
            Success, retval is an integer indicating the number of tagnames used by the user
        (1, None)
            Failure
    """
    return 1, None

