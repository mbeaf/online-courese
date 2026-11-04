from django.urls import path

from . import views

app_name = 'onlinecourse'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/submit/', views.exam, name='submit'),
    path('submissions/<int:submission_id>/', views.show_exam_result, name='show_exam_result'),
]
