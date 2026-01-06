from django.apps import AppConfig


class PaymentsConfig(AppConfig):
   name = 'CheersMe.payments'
   def ready(self):
        import CheersMe.payments.signals

