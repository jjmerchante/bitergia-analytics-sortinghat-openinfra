"""
SortingHat configuration for testing
"""

import logging
import sys

# Graphene logs SortingHat exceptions and Django prints them
# to the standard error output. This code prevents Django
# kind of errors are not shown.
if len(sys.argv) > 1 and sys.argv[1] == 'test':
    logging.disable(logging.CRITICAL)


SILENCED_SYSTEM_CHECKS = ["django_mysql.E016"]

SECRET_KEY = 'fake-key'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'graphene_django',
    'sortinghat.core',
]

SQL_MODE = [
    'NO_ZERO_IN_DATE',
    'NO_ZERO_DATE',
    'ERROR_FOR_DIVISION_BY_ZERO',
    'NO_AUTO_CREATE_USER',
    'NO_ENGINE_SUBSTITUTION',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'root',
        'PASSWORD': 'root',
        'NAME': 'sortinghat_db',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'sql_mode': ','.join(SQL_MODE)
        },
        'TEST': {
            'NAME': 'testhat',
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_520_ci',
        },
        'HOST': '127.0.0.1',
        'PORT': 3306
    }
}

USE_TZ = True
