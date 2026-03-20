"""
WSGI config for finance_tracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Resolve the project root directory relative to this file
# finance_tracker/wsgi.py -> parent = finance_tracker -> parent = root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from the project root
load_dotenv(os.path.join(BASE_DIR, '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')

application = get_wsgi_application()
