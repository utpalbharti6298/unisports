from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        try:
            from accounts.models import User
            if User.objects.count() == 0:
                import seed_db
                seed_db.seed()
        except Exception:
            pass
