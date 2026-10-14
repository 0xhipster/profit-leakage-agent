import sys
from tools import load_data, clean_data, calculate_by_group, make_bar_chart

table, _ = load_data(sys.argv[1])
cleaned, _ = clean_data(
    table,
    drop_columns=["Market2", "weeknum"],
    date_columns=["Order.Date", "Ship.Date"],
)

grouped, _ = calculate_by_group(cleaned, "Category")
path, summary = make_bar_chart(
    grouped,
    label_column="Category",
    value_column="margin_pct",
    highlight="Furniture",
    title="Furniture earns a 6.9% margin, about half the rate of the other two categories",
    subtitle="Profit margin by category, 2011 to 2014 (total profit divided by total sales)",
    source="Source: Global Superstore (Kaggle, fatihilhan), 51,290 line items, 2011 to 2014.",
    number_format="percent",
    name="test_category_margin",
)
print(summary)
print()
print("Benchmark to compare: Furniture 6.94%, Office Supplies 13.69%, Technology 13.99%")
print("Now open the picture:", path)
