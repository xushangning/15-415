import os
import getpass

"""
	Constants
"""
DBNAME = getpass.getuser()
COOKIE_USERNAME_FLAG = "uname"

# Sqlite
DB_FILE = os.path.abspath(os.getcwd()) + "/hw7.db" 

# Postgres
DB_DESC = "dbname=%s user=%s" % (DBNAME, DBNAME)

# Error prompt
err_internal = "Internal error, refresh page to try again"
err_login =  "Please login"
err_invalid_input =  "Invalid input"

# Result status
SUCCESS = 0
FAILURE = 1
DB_ERROR = -1
DB_CONNECTION_ERROR = -2