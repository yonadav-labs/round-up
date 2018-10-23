__author__ = 'JLCJ'
from django.apps import AppConfig


class Main_AppConfig(AppConfig):
    name = 'main_app'
    verbose_name = 'Main App'

    def ready(self):
        import signals.handlers
        import main_app.tasks
