import sys
from tools import load_data

table, summary = load_data(sys.argv[1])
print(summary)
