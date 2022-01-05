"""
A simple sanity checker
"""

# Import necessary packages
import paper.database_wrapper as db_wrapper
import paper.functions as funcs
from paper.constants import *

from datetime import datetime
from datetime import timedelta

"""
Test constants
"""

USERS = ["foo", "bar", "foofoo", "barbar", "foobar"]
TITLES = ["1", "2", "3", "4", "5"]
DESCS = ["This is just the desc1"]
TEXTS = ["I have an apple. I have a pen. --> ApplePen",
         "I have a pineapple. I have a pen. --> PineapplePen",
         "ApplePen. PineapplePen. --> PenPineappleApplePen",
         "Why this is popular?",
         "PPAP PPAP PPAP PPAP"]
TAGS = ["tag1", "tag2", "tag3", "tag4"]

ALL_FUNCS = ['add_new_paper', 'delete_paper', 'get_paper_tags',
             'get_papers_by_keyword', 'get_papers_by_tag',
             'get_papers_by_liked', 'get_most_active_users',
             'get_most_popular_papers', 'get_most_popular_tag_pairs',
             'get_most_popular_tags', 'get_number_papers_user', 'get_number_tags_user',
             'get_number_liked_user', 'get_recommend_papers', 'get_timeline',
             'get_timeline_all', 'get_likes', 'login', 'reset_db',
             'signup', 'unlike_paper', 'like_paper']
RES = {}
VERBOSE = False


def report_result():
    # Report result
    print("**********************************")
    print("*          TEST RESULTS          *")
    print("**********************************")
    pass_tests = []
    failed_tests = []
    not_tested = []
    for func_name in ALL_FUNCS:
        if func_name in RES:
            if RES[func_name] is True:
                pass_tests.append(func_name)
            else:
                failed_tests.append(func_name)
        else:
            not_tested.append(func_name)
    maxlen = len(max(ALL_FUNCS, key=len))
    for t in sorted(failed_tests, key=len):
        print("[%s]: Failed" % t.ljust(maxlen))
    for t in sorted(not_tested, key=len):
        print("[%s]: Not tested" % t.ljust(maxlen))
    for t in sorted(pass_tests, key=len):
        print("[%s]: Pass" % t.ljust(maxlen))


def exit_test():
    report_result()
    exit(1)


def error_message(func, msg, should_abort = True):
    RES[func.__name__] = False
    print("[Error in %s]: %s" % (func.__name__, msg))
    if should_abort:
        exit_test()


def format_error(func, should_abort = True):
    error_message(func, "incorrect return value format", should_abort)


def status_error(func, should_abort = True):
    error_message(func, "failed unexpectedly", should_abort)


def db_wrapper_debug(func, argdict, verbose = VERBOSE):
    if verbose:
        msg = "[Test] %s(" % func.__name__
        for k,v in argdict.items():
            msg += " %s = %s," % (str(k), str(v))
        msg += " )"
        print(msg)
    res = db_wrapper.call_db(func, argdict)
    if verbose:
        print("\treturn: %s" % str(res))
    return res


if __name__ == "__main__":
    # Reset the database
    RES[funcs.reset_db.__name__] = True
    try:
        status, res = db_wrapper_debug(funcs.reset_db, {})
        if status != SUCCESS:
            status_error(funcs.reset_db)

    except TypeError:
        format_error(funcs.reset_db)

    # Test signup
    RES[funcs.signup.__name__] = True
    try:
        for user in USERS:
            status, res = db_wrapper_debug(funcs.signup, {'uname':user, 'pwd':user})
            if status != SUCCESS:
                status_error(funcs.signup)
    except TypeError:
        format_error(funcs.signup)

    # Test login
    RES[funcs.login.__name__] = True
    try:
        status, res = db_wrapper_debug(funcs.login, {'uname':USERS[0], 'pwd':USERS[0]})
        if status != SUCCESS:
            status_error(funcs.login,)
        status, res = db_wrapper_debug(funcs.login, {'uname':USERS[0], 'pwd':USERS[1]})
        if status == SUCCESS:
            error_message(funcs.login, "password is not matched but still return login success")
    except TypeError:
        format_error(funcs.login)

    # Test new papers
    RES[funcs.add_new_paper.__name__] = True
    pids = []
    try:
        tag_count = len(TAGS)
        for pid in range(len(TITLES)):
            status, res = db_wrapper_debug(funcs.add_new_paper, {'uname':USERS[0], 'title':TITLES[pid],
                                            'desc':DESCS[0], 'text':TEXTS[pid],
                                            'tags':[TAGS[pid % tag_count], TAGS[(pid+1) % tag_count], TAGS[(pid+2) % tag_count]]}
                                        )
            if status != SUCCESS:
                status_error(funcs.add_new_paper)
            else:
                test_pid = int(res)
                pids.append(test_pid)
    except (TypeError, ValueError):
        format_error(funcs.add_new_paper)

    # Test like
    RES[funcs.like_paper.__name__] = True
    try:
        for likes in [[1, 1], [2, 1], [2, 2], [2, 3], [3, 1], [3, 3]]:
            status, res = db_wrapper_debug(funcs.like_paper, {'uname':USERS[likes[0]], 'pid':likes[1]})
            if status != SUCCESS:
                status_error(funcs.like_paper)
    except TypeError:
        format_error(funcs.like_paper)

    # Test list papers
    list_funcs_ctx = [
        (funcs.get_timeline, [5, 4, 3, 2, 1], {'uname':USERS[0]}),
        (funcs.get_timeline_all, [5, 4, 3, 2, 1], {}),
        (funcs.get_papers_by_tag, [5, 4, 3, 1], {'tag':TAGS[0]}),
        (funcs.get_papers_by_keyword, [2], {'keyword':'pineapple'}),
        (funcs.get_papers_by_liked, [1], {'uname':USERS[1]}),
        (funcs.get_most_popular_papers, [1, 3, 2], {'begin_time':datetime.now() + timedelta(days=-1)}),
        (funcs.get_recommend_papers, [3, 2], {'uname':USERS[1]}),
    ]

    for func, ans, args in list_funcs_ctx:
        RES[func.__name__] = True
        try:
            status, res = db_wrapper_debug(func, args)
            if status != SUCCESS:
                status_error(func,)
            else:
                pids_return = []
                for paper in res:
                    if len(paper) != 5:
                        raise TypeError("paper tuple length ts not 5")
                    else:
                        pids_return.append(paper[0])
                if pids_return != ans:
                    error_message(func, "expect pids %s but return %s" % (ans, pids_return))
        except (TypeError, ValueError):
                format_error(func)

    # Test directly test return values
    value_func_ctx = [
        (funcs.get_likes, 3, {'pid':1}),
        (funcs.get_most_active_users, [USERS[0]], {'count':1}),
        (funcs.get_most_popular_tags, [(TAGS[0], 4)], {'count':1}),
        (funcs.get_most_popular_tag_pairs, [(TAGS[0], TAGS[1], 3)], {'count':1}),
        (funcs.get_number_papers_user, 5, {'uname':USERS[0]}),
        (funcs.get_number_tags_user, 4, {'uname':USERS[0]}),
        (funcs.get_number_liked_user, 3, {'uname':USERS[2]}),
        (funcs.get_paper_tags, ['tag1', 'tag2', 'tag3'], {'pid':1}),
    ]

    for func, ans, args in value_func_ctx:
        RES[func.__name__] = True
        try:
            status, res = db_wrapper_debug(func, args)
            if status != SUCCESS:
                status_error(funcs.get_likes,)
            else:
                if ans != res:
                    error_message(func, "expect %s but return %s" % (ans, res))
        except (TypeError, ValueError):
            format_error(func)

    # Test functions with no return value
    none_func_ctx = [
        (funcs.unlike_paper, {'uname':USERS[1], 'pid':1}),
        (funcs.delete_paper, {'pid':1}),
    ]

    for func, args in none_func_ctx:
        RES[func.__name__] = True
        try:
            status, res = db_wrapper_debug(func, args)
            if status != SUCCESS:
                status_error(func,)
        except (TypeError, ValueError):
            format_error(func)

    # Reset database
    db_wrapper_debug(funcs.reset_db, {})
    report_result()