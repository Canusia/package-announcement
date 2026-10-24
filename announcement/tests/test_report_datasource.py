import datetime
import importlib.util

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import Group

from cis.models.customuser import CustomUser
from cis.models.teacher import Teacher, TeacherHighSchool, TeacherCourseCertificate
from cis.models.highschool import HighSchool
from cis.models.course import Course, Cohort

if importlib.util.find_spec('report.report'):
    from report.report.models.report import Report
else:
    from report.models.report import Report

from announcement.announcement.datasources.report_datasource import ReportDataSource


class ReportDataSourceTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='instructor')
        self.report = Report.objects.create(
            app='cis', name='teacher_certificates',
            title='Teacher Course Certificates',
            description='x', categories=['Instructors'], available_for=['ce'])
        u = CustomUser.objects.create(username='i', email='i@x.com',
                                      first_name='Pat', last_name='Lee')
        t = Teacher.objects.create(user=u, status='active')
        hs = HighSchool.objects.create(name='HS', status='Active')
        ths = TeacherHighSchool.objects.create(teacher=t, highschool=hs, status='In the Program')
        course = Course.objects.create(
            name='ENGL& 101', title='Eng', catalog_number='101',
            cohort=Cohort.objects.create(name='Eng', designator='ENGL'), status='Active')
        TeacherCourseCertificate.objects.create(
            teacher_highschool=ths, course=course, status='Teaching',
            expires_on=timezone.localdate() + datetime.timedelta(days=30))

    def test_report_datasource_yields_name_and_email(self):
        ds = ReportDataSource(str(self.report.id))
        rows = ds.data_source({'certificate_status': ['Teaching'], 'highschools': []})
        self.assertTrue(rows)
        self.assertEqual(rows[0]['email'], ['i@x.com'])
        self.assertEqual(rows[0]['FirstName'], 'Pat')

    def test_title_and_descriptor_from_report(self):
        ds = ReportDataSource(str(self.report.id))
        self.assertEqual(ds.title(), 'Teacher Course Certificates')
        self.assertTrue(ds.short_descriptor())

    def test_recipients_summary_is_generic_not_teacher_worded(self):
        ds = ReportDataSource(str(self.report.id))
        html = ds.recipients_summary({'certificate_status': ['Teaching'], 'highschools': []})
        self.assertIn('recipient', html.lower())
        self.assertNotIn('teacher recipients', html.lower())
        # shows the count (1 recipient from setUp)
        self.assertIn('1', html)
