"""Registration-summary datasources treat the term filter as a term tree.

A section has one `term`; the registration term is its parent. Filtering by a
parent term must therefore include sections on its sub-terms.
"""
from unittest.mock import patch

from django.test import TestCase

from cis.models.highschool import HighSchool
from cis.models.section import ClassSection

from cis.models.highschool_administrator import (
    HSAdministrator, HSAdministratorPosition, HSPosition)
from cis.models.teacher import Teacher
from cis.tests.term_tree_fixtures import TermTreeFixtureMixin, sfx

from announcement.announcement.datasources.registration_summary_highschools import (
    registration_summary_highschools_DS)
from announcement.announcement.datasources.registration_summary_teachers import (
    registration_summary_teachers_DS)


class RegistrationSummaryTermTreeTests(TermTreeFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username=f't_{sfx()}', email=f't_{sfx()}@x.com', password='x')
        self.teacher = Teacher.objects.create(user=user)
        self.sections['Fall Semester'].teacher = self.teacher
        self.sections['Fall Semester'].save()

        hs_user = User.objects.create_user(
            username=f'h_{sfx()}', email=f'h_{sfx()}@x.com', password='x')
        self.position = HSPosition.objects.create(name=f'Pos-{sfx()}')
        HSAdministratorPosition.objects.create(
            hsadmin=HSAdministrator.objects.create(user=hs_user),
            highschool=self.hs, position=self.position, status='active')

    def test_teachers_summary_by_parent_term_includes_sub_term_sections(self):
        ds = registration_summary_teachers_DS()
        self.assertEqual(
            ds.data_source({'term': [str(self.quarter.id)]}, count=True), 1)

    def test_teachers_summary_by_sub_term_still_matches(self):
        ds = registration_summary_teachers_DS()
        self.assertEqual(
            ds.data_source({'term': [str(self.semester.id)]}, count=True), 1)
        self.assertEqual(
            ds.data_source({'term': [str(self.spring.id)]}, count=True), 0)

    def test_highschool_summary_by_parent_term_includes_sub_term_sections(self):
        ds = registration_summary_highschools_DS()
        filters = {'term': [str(self.quarter.id)],
                   'role': [str(self.position.id)]}
        self.assertEqual(ds.data_source(filters, count=True), 1)


class SummaryTermsPassedTests(TermTreeFixtureMixin, TestCase):
    """sections_summary gets the picked term plus sub-terms; merge field is the pick."""

    def _empty_summary(self):
        from django.db.models import QuerySet
        none = ClassSection.objects.none()
        return (none, none, none, none, 0, 0)

    def _user(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.create_user(
            username=f'u_{sfx()}', email=f'u_{sfx()}@x.com', password='x')

    def test_teachers_receive_expanded_terms_and_row_uses_picked(self):
        teacher = Teacher.objects.create(user=self._user())
        section = self.sections['Fall Semester']
        section.teacher = teacher
        section.save()
        with patch.object(Teacher, 'sections_summary', create=True,
                          return_value=self._empty_summary()) as m:
            rows = registration_summary_teachers_DS().data_source(
                {'term': [str(self.quarter.id)], 'mode': ['live']})
        passed = {t.id for t in m.call_args.kwargs['terms']}
        self.assertEqual(passed, {self.quarter.id, self.semester.id, self.trimester.id})
        self.assertEqual(rows[0]['TermID'], str(self.quarter.id))
        self.assertEqual(rows[0]['Term'], str(self.quarter))

    def test_highschools_receive_expanded_terms_and_row_uses_picked(self):
        position = HSPosition.objects.create(name=f'Pos-{sfx()}')
        HSAdministratorPosition.objects.create(
            hsadmin=HSAdministrator.objects.create(user=self._user()),
            highschool=self.hs, position=position, status='active')
        self.sections['Fall Semester']  # section on a sub-term, school = self.hs
        with patch.object(HighSchool, 'sections_summary', create=True,
                          return_value=self._empty_summary()) as m:
            rows = registration_summary_highschools_DS().data_source(
                {'term': [str(self.quarter.id)], 'role': [str(position.id)]})
        passed = {t.id for t in m.call_args.kwargs['terms']}
        self.assertEqual(passed, {self.quarter.id, self.semester.id, self.trimester.id})
        self.assertEqual(rows[0]['TermID'], str(self.quarter.id))
