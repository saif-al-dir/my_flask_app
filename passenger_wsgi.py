import sys
import os

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
INTERP = os.path.join(PROJECT_DIR, 'venv', 'bin', 'python')

if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import create_app
application = create_app()

if __name__ == "__main__":
    application.run(debug=True)