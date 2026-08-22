import sys
import os

# 1. Get the directory where this file is located
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))

# 2. Manually add the venv's site-packages to sys.path
# This is the bulletproof MyDevil fix!
VENV_SITE_PACKAGES = os.path.join(PROJECT_DIR, 'venv', 'lib', 'python3.11', 'site-packages')
if VENV_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, VENV_SITE_PACKAGES)

# 3. Add the project directory to sys.path so it finds the 'app' folder
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 4. Now import and create your Flask app
from app import create_app
application = create_app()

if __name__ == "__main__":
    application.run(debug=True)