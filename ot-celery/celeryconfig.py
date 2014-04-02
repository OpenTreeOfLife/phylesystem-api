# See http://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html#broker-redis
BROKER_URL = 'redis://localhost:6379/0'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}  # 1 hour.
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT=['json']
#CELERY_TIMEZONE = 'Europe/Oslo'
CELERY_ENABLE_UTC = True