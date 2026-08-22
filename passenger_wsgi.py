import sys
import os
import site

# 1. Get the directory where this file is located
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))

# 2. Define the path to the venv's site-packages
VENV_SITE_PACKAGES = os.path.join(PROJECT_DIR, 'venv', 'lib', 'python3.11', 'site-packages')

# 3. Use site.addsitedir to properly add the venv to the path
# This is the standard, bulletproof way to load a venv in Python
site.addsitedir(VENV_SITE_PACKAGES)

# 4. Add the project directory to sys.path so it finds the 'app' folder
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 5. Now import and create your Flask app
from app import create_app
application = create_app()

if __name__ == "__main__":
    application.run(debug=True)