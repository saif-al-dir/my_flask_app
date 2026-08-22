import sys
import os

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
INTERP = os.path.join(PROJECT_DIR, 'venv', 'bin', 'python')

from app import create_app
application = create_app()

if __name__ == "__main__":
    application.run(debug=True)