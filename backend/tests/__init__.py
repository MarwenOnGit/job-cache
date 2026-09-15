import os
import sys

# Put the backend/ dir on sys.path so tests can `import db`, `import ranker`, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
