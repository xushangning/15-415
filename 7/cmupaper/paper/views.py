from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from pytz import timezone
from datetime import timedelta
from datetime import datetime
import textract

from .constants import *
from .database_wrapper import *
from . import functions
import tempfile

"""
Utility functions
"""


def get_datetime(delta = timedelta(0)):
    """
    Get a datetime object of current time plus a timedelta
    """
    return datetime.now(timezone("US/Eastern")) + delta


def get_current_user(request):
    """
    Get the user name from a cookie.
    XXX: It's definitely not the thing you should do when you implement your own website...
    """
    cookie = request.COOKIES.get(COOKIE_USERNAME_FLAG)
    return cookie


def set_login(response, uname):
    """
    Set the user name in the cookie.
    XXX: Don't do this for production...
    """
    response.set_cookie(COOKIE_USERNAME_FLAG, uname)


def reset_login(response):
    """
    Reset the cookie
    """
    response.delete_cookie(COOKIE_USERNAME_FLAG)


def get_upload_dir_path():
    """
    Helper function to get the directory storing uploaded files.
    """
    return str(os.path.join(settings.BASE_DIR, 'media'))


def get_upload_file_path(pid):
    """
    Construct a file path based on pid
    """
    return get_upload_dir_path() + "/" + str(pid) + ".pdf"


def valid_login(request):
    """
    Validate a user has logged in by setting cookie.
    XXX: Don't do this for production
    """
    cookie = get_current_user(request)
    if cookie is None:
        return False
    return True


def append_likes_tags(conn, posts):
    """
    Utility to append like counts and tags of a given paper
    """
    likes = list()
    tag_lists = list()
    for post in posts:
        # get like count for the post
        status, likec = call_db_with_conn(conn, functions.get_likes, {'pid':int(post['pid'])})
        if status == SUCCESS:
            likes.append(int(likec))
        else:
            likes.append(0)
        # get all the tags for the post
        status, tags = call_db_with_conn(conn, functions.get_paper_tags, {'pid':int(post['pid'])})
        if status == SUCCESS:
            tag_lists.append(tags)
        else:
            tag_lists.append(list())

    for i in range(len(posts)):
        posts[i]['like'] = likes[i]
        posts[i]['tags'] = tag_lists[i]


def get_paper_dict(paper_list):
    try:
        return \
            [{'pid':x[0], 'username':x[1], 'title':x[2], 'begin_time':x[3], 'desc':x[4]} for x in paper_list]
    except (IndexError, KeyError) as e:
        print("[TA Hints] May be your return value is not in the correct format")
        raise e

"""
Views
"""


def reset(request):
    """
    Reset the database
    """
    state, res = call_db(functions.reset_db, {})
    context = dict()
    if state != SUCCESS:
        context['message'] = "Failed"
    else:
        context['message'] = "Success"
        # Delete all uploaded files
        upload_dir = get_upload_dir_path()
        for file in os.listdir(upload_dir):
            if os.path.isfile(file):
                try:
                    os.remove(file)
                except:
                    print("Can not remove file %s" % file)
    return render(request, 'paper/reset.html', context)


def logout(request):
    """
    Handle log out request
    """
    response = HttpResponseRedirect(reverse('paper:home'))
    reset_login(response)
    return response


def login(request):
    """
    Login page
    """
    if request.method == 'POST':
        try:
            uname = request.POST['username']
            pwd = request.POST['password']
        except KeyError:
            return render(request, 'paper/login.html', {'error_message': err_login})

        state, res = call_db(functions.login, {"uname":uname, "pwd":pwd})
        if state != SUCCESS:
            return render(request, 'paper/login.html',
                    {'error_message':"Incorrect username or password."})
        else:
            response = HttpResponseRedirect(reverse('paper:home'))
            set_login(response, uname)
            return response
    else:
        return render(request, 'paper/login.html', {'error_message': err_login})


def signup(request):
    """
    Signup page
    """
    if request.method == 'POST':
        uname = request.POST['username']
        pwd1 = request.POST['password1']
        pwd2 = request.POST['password2']
        if pwd1 == "" or pwd2 == "" or uname == "":
            return render(request, 'paper/signup.html', {'error_message':err_invalid_input})
        if pwd1 != pwd2:
            return render(request, 'paper/signup.html', {'error_message':"Passwords do not match."})
        state, res = call_db(functions.signup, {'uname':uname, 'pwd':pwd1})
        if state != SUCCESS:
            return render(request, 'paper/signup.html', {'error_message':"User exists"})
        response = HttpResponseRedirect(reverse('paper:home'))
        set_login(response, uname)
        return response
    elif request.method == 'GET':
        return render(request, 'paper/signup.html')


def home(request, err_msg = None):
    """
    Show the home page
    """
    # Validate login
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': err_login})
    uname = get_current_user(request)

    # Init context
    context = dict()
    context['username'] = get_current_user(request)
    context['error_message'] = err_msg
    context['home'] = True
    context['source'] = 'home'
    context['header_text'] = "Hello " + uname + "!"

    # Setup connection
    conn = None
    try:
        status, conn = get_db_connection()
        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        # Get timeline
        status, timeline_papers = call_db_with_conn(conn, functions.get_timeline, {'uname':uname})
        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        if len(timeline_papers) == 0:
            context['error_message'] = "No post posted"

        # Get liked
        status, liked_papers = call_db_with_conn(conn, functions.get_papers_by_liked, {'uname':uname})
        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        if len(liked_papers) == 0:
            context['error_message2'] = "Not any liked posts"

        # Get recommendation
        status, recommend_papers = call_db_with_conn(conn, functions.get_recommend_papers, {'uname':uname})
        if status != SUCCESS:
            context['error_message'] = err_internal
            close_db_connection(conn)
            return render(request, 'paper/base_paper_list.html', context)

        if len(recommend_papers) == 0:
            context['error_message3'] = "Not any recommendation posts"

        # Get statistics
        status, num_post = call_db_with_conn(conn, functions.get_number_papers_user, {'uname':uname})
        status, num_like = call_db_with_conn(conn, functions.get_number_liked_user, {'uname':uname})
        status, num_tag = call_db_with_conn(conn, functions.get_number_tags_user, {'uname':uname})

        recommend_paper_dicts = get_paper_dict(recommend_papers)
        liked_paper_dicts = get_paper_dict(liked_papers)
        timeline_paper_dicts = get_paper_dict(timeline_papers)
        append_likes_tags(conn, recommend_paper_dicts)
        append_likes_tags(conn, liked_paper_dicts)
        append_likes_tags(conn, timeline_paper_dicts)
        context['paper_list'] = timeline_paper_dicts
        context['liked_list'] = liked_paper_dicts
        context['recommend_list'] = recommend_paper_dicts
        context['num_post'] = num_post
        context['num_like'] = num_like
        context['num_tag'] = num_tag

        response = render(request, 'paper/base_paper_list.html', context)
        return response
    finally:
        if conn is not None:
            close_db_connection(conn)


def popular_papers(request, err_msg = None):
    """
    The popular paper page
    """
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': "Please login."})
    # Init context
    context = dict()
    context['username'] = get_current_user(request)
    context['error_message'] = err_msg
    context['popular'] = True
    context['source'] = 'popular'
    context['header_text'] = "What's new"

    # setup connection
    conn = None
    try:
        status, conn = get_db_connection()
        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        # get popular papers
        status, popular_paper_list = call_db_with_conn(conn, functions.get_most_popular_papers,
                                                   {'begin_time':get_datetime(timedelta(days=-14))})
        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        if len(popular_paper_list) == 0:
            context['error_message'] = "Not any popular papers now, publish your own and become popular!"

        # get recent papers
        status, recent_paper_list = call_db_with_conn(conn, functions.get_timeline_all, {})

        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        if len(recent_paper_list) == 0:
            context['error_message2'] = "Not any recent papers"

        # Get global statistics
        status, active_user = call_db_with_conn(conn, functions.get_most_active_users, {})
        status, popular_tag = call_db_with_conn(conn, functions.get_most_popular_tags, {})
        status, popular_tag_pair = call_db_with_conn(conn, functions.get_most_popular_tag_pairs, {})
        active_user = active_user[0] if len(active_user) > 0 else ""
        popular_tag = popular_tag[0] if len(popular_tag) > 0 else ""
        popular_tag_pair = popular_tag_pair[0][0] + ", " + popular_tag_pair[0][1] if len(popular_tag_pair) > 0 else ""

        popular_papers_dicts = get_paper_dict(popular_paper_list)
        recent_papers_dicts = get_paper_dict(recent_paper_list)
        append_likes_tags(conn, popular_papers_dicts)
        append_likes_tags(conn, recent_papers_dicts)

        context['paper_list'] = popular_papers_dicts
        context['recent_list'] = recent_papers_dicts
        context['active_user'] = active_user
        context['popular_tag'] = popular_tag
        context['popular_pair'] = popular_tag_pair
        response = render(request, 'paper/base_paper_list.html', context)

        return response
    finally:
        if conn is not None:
            close_db_connection(conn)


def search_view(request):
    """
    Search result page
    """
    # Verify login
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': err_login})

    if request.method == 'POST' and request.POST['keywords'] != "":
        keywords = request.POST['keywords']
        # Init context
        context = dict()
        context['username'] = get_current_user(request)
        context['search'] = True
        context['source'] = 'search'
        context['header_text'] = 'Search results for \"' + keywords + "\""
        # Setup connection
        conn = None
        try:
            status, conn = get_db_connection()
            if status != SUCCESS:
                context['error_message'] = err_internal
                return render(request, 'paper/base_paper_list.html', context)

            # Get search result
            status, res_paper_list = call_db_with_conn(conn, functions.get_papers_by_keyword, {'keywords':keywords})
            if status != SUCCESS:
                context['error_message'] = err_internal
                return render(request, 'paper/base_paper_list.html', context)

            if len(res_paper_list) == 0:
                context['error_message'] = "No post posted"
                return render(request, 'paper/base_paper_list.html', context)

            res_paper_dicts = get_paper_dict(res_paper_list)
            append_likes_tags(conn, res_paper_dicts)
            context['paper_list'] = res_paper_dicts
            response = render(request, 'paper/base_paper_list.html', context)
            return response
        finally:
            if conn is not None:
                close_db_connection(conn)
    else:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def tag_view(request, tag_name):
    """
    Result page when clicking a  tag
    """
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': err_login})
    # Init context
    context = dict()
    context['username'] = get_current_user(request)
    context['tag_view'] = True
    context['source'] = 'tag_view'
    context['header_text'] = 'Posts with #' + tag_name
    # Setup connection
    conn = None
    try:
        status, conn = get_db_connection()
        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        # Get search result
        status, res_paper_list = call_db_with_conn(conn, functions.get_papers_by_tag, {'tag':tag_name})
        if status != SUCCESS:
            context['error_message'] = err_internal
            return render(request, 'paper/base_paper_list.html', context)

        if len(res_paper_list) == 0:
            context['error_message'] = "No post posted"
            return render(request, 'paper/base_paper_list.html', context)

        res_paper_dicts = get_paper_dict(res_paper_list)
        append_likes_tags(conn, res_paper_dicts)
        context['paper_list'] = res_paper_dicts
        response = render(request, 'paper/base_paper_list.html', context)
        return response
    finally:
        if conn is not None:
            close_db_connection(conn)


def new_paper(request):
    """
    Create a new paper
    """
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': err_login})
    # Init context
    context = dict()
    context['new_paper'] = True
    context['header_text'] = "New posts"

    if request.method == 'POST' and request.FILES.get('post_pdf'):
        # Setup connection
        conn = None
        try:
            status, conn = get_db_connection()
            if status != SUCCESS:
                context['error_message'] = err_internal
                return render(request, 'paper/base_paper_list.html', context)

            uname = get_current_user(request)
            title = request.POST['title']
            desc = request.POST['desc']
            pdf_file = request.FILES.get('post_pdf')
            fs = FileSystemStorage()
            # verify input
            if title == "":
                context['error_message'] = err_invalid_input;
                return render(request, 'paper/base_paper_list.html', context)
            if pdf_file.name.endswith(".pdf") is False:
                context['error_message'] = "Invalid file type"
                return render(request, 'paper/base_paper_list.html', )
            # read  tags
            tags_str = request.POST['tags']
            tags = [str(x).strip() for x in str(tags_str).split(',')]
            # save the uploaded file
            filename = fs.save(pdf_file.name, pdf_file)
            file_path = get_upload_dir_path()
            file_uploaded = file_path + "/" + filename
            # extract text from pdf
            text = textract.process(file_uploaded)
            status, pid = call_db_with_conn(
                    conn, functions.add_new_paper, {'uname':uname, 'title':title, 'desc':desc, 'text':text, 'tags':tags})
            if status == SUCCESS:
                try:
                    os.rename(file_uploaded, get_upload_file_path(pid))
                except:
                    print("[Error] Can not move file")
                return home(request)
            else:
                context['error_message'] = "Can not upload, try again"
                # remove the uploaded file
                try:
                    os.remove(file_uploaded)
                except:
                    pass
                return render(request, 'paper/base_paper_list.html', context)
        finally:
            if conn is not None:
                close_db_connection(conn)
    else:
        return render(request, 'paper/base_paper_list.html', context)


def delete_paper(request, paper_id):
    """
    Delete a paper
    """
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': err_login})
    status, res = call_db(functions.delete_paper, {'pid':int(paper_id)})
    if status == SUCCESS:
        filename = str(os.path.join(settings.BASE_DIR, 'media')) + "/" + paper_id + ".pdf"
        try:
            os.remove(filename)
        except:
            print("[Error] Can not remove file")
    return home(request)


def view_paper(request, paper_id):
    """
    View the pdf file of a paper
    """
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': err_login})
    filename = get_upload_file_path(paper_id)
    with open(filename, 'r') as pdf:
        response = HttpResponse(pdf.read(), content_type="application/pdf")
        response['Content-Disposition'] = 'filename=' + paper_id + ".pdf"
        return response


def like(request, paper_id, source):
    return like_helper(request, paper_id, source, True)


def unlike(request, paper_id, source):
    return like_helper(request, paper_id, source, False)


def like_helper(request, paper_id, source, like):
    if not valid_login(request):
        return render(request, 'paper/login.html', {'error_message': err_login})
    uname = get_current_user(request)
    status = SUCCESS
    res = None
    if like:
        status, res = call_db(functions.like_paper, {'uname':uname, 'pid':int(paper_id)})
    else:
        status, res = call_db(functions.unlike_paper, {'uname':uname, 'pid':int(paper_id)})
    err_msg = "Invalid like" if status != SUCCESS else None
    return popular_papers(request, err_msg) if source == "popular" else home(request, err_msg)
