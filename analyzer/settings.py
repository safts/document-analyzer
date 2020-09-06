import os

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost/0')
