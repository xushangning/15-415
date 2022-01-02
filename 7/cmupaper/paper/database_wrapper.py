import psycopg2 as psy

from constants import *


def get_db_connection():
    """
    Get a postgres database connection
    """
    try:
        conn = psy.connect(DB_DESC)
        return SUCCESS, conn
    except psy.DatabaseError, e:
        print "Error %s" % e
        return DB_CONNECTION_ERROR, None


def call_db_with_conn(conn, function_name, argdict):
    """
    Call a db API via the given connection
    """
    try:
        return function_name(conn, **argdict)
    except psy.DatabaseError, e:
        print "Error %s: " % e.args[0]
        conn.rollback()
        return DB_ERROR, None


def close_db_connection(conn):
    """
    Safely close a database connection. Ignore any error.
    """
    try:
        conn.close()
    except:
        pass


def call_db(function_name, argdict):
    """
    Make a one shot request to the database. Ignore any error when closing the connection.
    """
    conn = None
    try:
        res, conn = get_db_connection()
        if res != SUCCESS:
            return res, None
        return function_name(conn, **argdict)
    except psy.DatabaseError, e:
        print "Error %s: " % e.args[0]
        conn.rollback()
        return DB_ERROR, None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
