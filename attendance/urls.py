from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_student, name='register_student'),
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('video_feed/', views.video_feed,
         name='video_feed'),  # keep this for now
    path('attendance_table/', views.show_attendance, name='attendance_table'),
]
