"""
    HS Admin URL Configuration
"""
from django.urls import path

from important_link.views.views import (
    show_links_for_highschool_admin
)

app_name = 'highschool_admin_important_links'
urlpatterns = [
    path('', show_links_for_highschool_admin, name='links'),
]
