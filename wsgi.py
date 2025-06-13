# wsgi.py
import os
import sys

# Add the project's root directory to the Python path to ensure modules are found
sys.path.insert(0, os.path.dirname(__file__))

from backend.app import create_app

# The WSGI server will look for this 'application' callable.
application = create_app()

