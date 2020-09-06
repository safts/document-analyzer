from __future__ import absolute_import, unicode_literals

from celery import Celery

app = Celery('analyzer', backend='redis://redis:6379/1', broker='redis://redis:6379/0')
app.autodiscover_tasks(['analyzer.analysis'])
