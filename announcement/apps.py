from django.apps import AppConfig

BMAILER_DS = [
    ('file_upload', 'File Upload'),
    ('highschool_admins', 'High School Administrators'),
    ('teachers', 'Teachers'),
    
    ('registration_summary_teachers', 'Registration Summary - For Teachers'),
    ('registration_summary_highschools', 'Registration Summary - For High Schools'),
]

class AnnouncementConfig(AppConfig):
    name = 'announcement'
