from django.apps import AppConfig


class AnnouncementConfig(AppConfig):
    name = 'announcement'

    def ready(self):
        import announcement.datasources  # noqa: F401 (registers bulk-mailer datasources)


class DevAnnouncementConfig(AppConfig):
    name = 'announcement.announcement'

    def ready(self):
        import announcement.announcement.datasources  # noqa: F401 (registers bulk-mailer datasources)
