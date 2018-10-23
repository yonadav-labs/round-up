__author__ = 'JLCJ'
from django.apps import AppConfig


class Lets_EncryptConfig(AppConfig):
    name = 'source.lib.lets_encrypt'
    verbose_name = 'Lets Encrypt'

    def ready(self):
        pass