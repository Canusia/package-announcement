import os
from django import forms
from django.template import Context, Template
from django.template.loader import get_template

from django.utils.safestring import mark_safe
from django.core.validators import RegexValidator, validate_email

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.models.teacher import Teacher

from .base import MyCE_BMailerDS, MyCE_BMailerForm


class teachers_DS(MyCE_BMailerDS):
    ...