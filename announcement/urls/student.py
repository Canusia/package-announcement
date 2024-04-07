"""
    Student URL Configuration
"""
from django.urls import path

from important_link.views.views import (
    show_links_for_students
)

app_name = 'student_important_links'
urlpatterns = [
    path('', show_links_for_students, name='links'),
]
