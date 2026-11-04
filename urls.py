from django.urls import path

from . import views

app_name = 'onlinecourse'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/submit/', views.submit_exam, name='submit_exam'),
    path('submissions/<int:submission_id>/', views.exam_result, name='exam_result'),
]
