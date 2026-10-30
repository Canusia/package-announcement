"""Registration-summary datasources treat the term filter as a term tree.

A section has one `term`; the registration term is its parent. Filtering by a
parent term must therefore include sections on its sub-terms.
"""
from django.test import TestCase

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
