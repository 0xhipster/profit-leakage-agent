import sys
from tools import load_data, clean_data, calculate_by_group

table, _ = load_data(sys.argv[1])
cleaned, _ = clean_data(
    table,
    drop_columns=["Market2", "weeknum"],
    date_columns=["Order.Date", "Ship.Date"],
)

for column in ["Category", "Market", "Year"]:
    _, summary = calculate_by_group(cleaned, column)
    print(summary)
    print()
