import sys
from tools import load_data, clean_data, calculate_by_group, export_table

table, _ = load_data(sys.argv[1])
cleaned, _ = clean_data(
    table,
    drop_columns=["Market2", "weeknum"],
    date_columns=["Order.Date", "Ship.Date"],
)

grouped, _ = calculate_by_group(cleaned, "Category")
path, summary = export_table(grouped, "test_category_profit")
print(summary)
print()

print("Check against the Power BI benchmark (Category):")
print("Furniture: sales 4,110,884, profit 285,204.72, margin 6.94%")
print("Office Supplies: sales 3,787,330, profit 518,473.83, margin 13.69%")
print("Technology: sales 4,744,691, profit 663,778.73, margin 13.99%")
print()
print("Now open the saved file and compare:", path)

print()
print("Bad file name test (this should be refused):")
try:
    export_table(grouped, "..\\escape")
except ValueError as problem:
    print("Refused:", problem)
