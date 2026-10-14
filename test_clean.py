import sys
from tools import load_data, clean_data

table, _ = load_data(sys.argv[1])
cleaned, report = clean_data(
    table,
    drop_columns=["Market2", "weeknum"],
    date_columns=["Order.Date", "Ship.Date"],
    duplicate_columns=[
        "Order.ID", "Product.ID", "Customer.ID", "Order.Date",
        "Sales", "Quantity", "Discount", "Profit", "Shipping.Cost",
    ],
)
print(report)
print()
print("Check against the Power BI anchors:")
print("Rows:", format(len(cleaned), ","))
print("Total Sales:", format(int(cleaned["Sales"].sum()), ","))
print("Total Profit:", format(round(cleaned["Profit"].sum(), 2), ",.2f"))
print("Discount distinct values:", cleaned["Discount"].nunique())
print("Order.Date type:", cleaned["Order.Date"].dtype)
print("Original table still has", len(table.columns), "columns")
