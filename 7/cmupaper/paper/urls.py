from django.urls import re_path

from . import views

app_name = 'paper'
urlpatterns = [
    re_path(r'^$', views.home, name='index'),
    re_path(r'^login/$', views.login, name='login'),
    re_path(r'^logout/$', views.logout, name='logout'),
    re_path(r'^home/$', views.home, name='home'),
    re_path(r'^signup/$', views.signup, name='signup'),
    re_path(r'^popular_papers/$', views.popular_papers, name='popular_papers'),
    re_path(r'^new_paper/$', views.new_paper, name='new_paper'),
    re_path(r'^like/(?P<paper_id>[0-9]+)/(?P<source>\w+)/$', views.like, name='like'),
    re_path(r'^unlike/(?P<paper_id>[0-9]+)/(?P<source>\w+)/$', views.unlike, name='unlike'),
    re_path(r'^delete_paper/(?P<paper_id>[0-9]+)$', views.delete_paper, name='delete_paper'),
    re_path(r'^view_paper/(?P<paper_id>[0-9]+)$', views.view_paper, name='view_paper'),
    re_path(r'^search_view/$', views.search_view, name='search_view'),
    re_path(r'^tag_view/(?P<tag_name>\w+)$', views.tag_view, name='tag_view'),
    re_path(r'^reset/$', views.reset, name='reset'),
]