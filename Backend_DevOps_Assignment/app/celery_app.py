import os
try:
	from celery import Celery
	CELERY_AVAILABLE = True
except Exception:
	Celery = None
	CELERY_AVAILABLE = False

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
if CELERY_AVAILABLE:
	# Name the Celery app with the project package and explicitly include
	# the tasks module so the worker imports it at startup and registers
	# task functions like `process_job`.
	celery = Celery('app', broker=REDIS_URL, backend=REDIS_URL, include=['app.tasks'])
else:
	celery = None
