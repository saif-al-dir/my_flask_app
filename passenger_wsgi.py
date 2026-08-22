import sys
import os

# Add the current directory to the sys.path so Passenger finds your 'app' folder
INTERP = os.path.dirname(os.path.realpath(__file__))
if INTERP not in sys.path:
    sys.path.insert(0, INTERP)

from app import create_app

# Passenger expects the variable to be named 'application'
application = create_app()

if __name__ == "__main__":
    # This allows you to run it locally using `python passenger_wsgi.py`
    application.run(debug=True)