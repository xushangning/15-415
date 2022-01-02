from django.conf.urls import url

from . import views

app_name = 'paper'
urlpatterns = [
    url(r'^$', views.home, name='index'),
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^home/$', views.home, name='home'),
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^popular_papers/$', views.popular_papers, name='popular_papers'),
    url(r'^new_paper/$', views.new_paper, name='new_paper'),
    url(r'^like/(?P<paper_id>[0-9]+)/(?P<source>\w+)/$', views.like, name='like'),
    url(r'^unlike/(?P<paper_id>[0-9]+)/(?P<source>\w+)/$', views.unlike, name='unlike'),
    url(r'^delete_paper/(?P<paper_id>[0-9]+)$', views.delete_paper, name='delete_paper'),
    url(r'^view_paper/(?P<paper_id>[0-9]+)$', views.view_paper, name='view_paper'),
    url(r'^search_view/$', views.search_view, name='search_view'),
    url(r'^tag_view/(?P<tag_name>\w+)$', views.tag_view, name='tag_view'),
    url(r'^reset/$', views.reset, name='reset'),
]