from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.home_view,           name='home'),
    path('login/',                        views.login_view,          name='login'),
    path('logout/',                       views.logout_view,         name='logout'),
    path('signup/',                       views.signup_view,         name='signup'),
    path('about/',                        views.about_view,          name='about'),
    path('dashboard/',                    views.dashboard_view,      name='dashboard'),
    path('directory/',                    views.directory_view,      name='directory'),
    path('profile/',                      views.profile_view,        name='profile'),
    path('profile/<str:student_id>/',     views.member_profile_view, name='member_profile'),
    path('delete/<str:student_id>/',      views.delete_member_view,  name='delete_member'),
    path('meetings/',                     views.meetings_view,       name='meetings'),
    path('meetings/new/',                 views.create_meeting_view, name='create_meeting'),
    path('meetings/<int:meeting_id>/',    views.meeting_detail_view, name='meeting_detail'),
    path('agenda/<int:meeting_id>/',      views.agenda_view,         name='agenda'),
    path('agenda/<int:meeting_id>/public/', views.public_agenda_view, name='public_agenda'),
    path('agenda/<int:meeting_id>/reorder/', views.agenda_reorder_view, name='agenda_reorder'),
    path('attendance/',                   views.attendance_view,     name='attendance'),
    path('attendance/<str:token>/',       views.session_qr_view,     name='session_qr'),
    path('checkin/<str:token>/',          views.checkin_view,        name='checkin'),
    path('test/',                         views.test_view,           name='test'),
    path('edit-site/',                    views.edit_site_view,      name='edit_site'),
]