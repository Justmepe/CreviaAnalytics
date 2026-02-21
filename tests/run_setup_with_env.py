from dotenv import load_dotenv
import runpy
import os

# Load .env from repo root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
# Run the setup test
runpy.run_path(os.path.join(os.path.dirname(__file__), 'setup_test.py'), run_name='__main__')
