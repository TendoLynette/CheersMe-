from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = 'CheersMe.dashboard'

def ready(self):
        import dashboard.signals 