import os

# Get the base directory of the project (the directory containing this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the data directory (assumes 'data' is at the same level as 'mitlesen')
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

VIDEOS_DIR = os.path.abspath(os.path.join(DATA_DIR, 'videos'))
COVERS_DIR = os.path.abspath(os.path.join(DATA_DIR, 'covers'))
DICTIONARIES_DIR = os.path.abspath(os.path.join(DATA_DIR, 'dictionaries'))
SPEECHES_DIR = os.path.abspath(os.path.join(DATA_DIR, 'speeches'))

# Video CSV files
VIDEOS_CSV_FILES = ["videos_es.csv", "videos_de.csv", "videos_ja.csv"]
