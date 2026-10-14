"""Makes the four tables for the Power BI dashboard, using the agent's own tools.

No internet, no API key, no cost. Each table is saved as a CSV in
output\\dashboard, and the export tool reads every file back and checks it.

Run: python make_dashboard_tables.py superstore.csv
"""

import os
import sys

import tools

DUPLICATES = ["Order.ID", "Product.ID", "Customer.ID", "Order.Date", "Sales", "Quantity", "Discount", "Profit", "Shipping.Cost"]
FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "dashboard")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data_path = sys.argv[1]
    raw, _ = tools.load_data(data_path)
    clean, report = tools.clean_data(
        raw, drop_columns=["Market2", "weeknum"], date_columns=["Order.Date", "Ship.Date"], duplicate_columns=DUPLICATES
    )
    print(report)

    jobs = [
        ("dash_discount_band", dict(group_by="Discount", cutoffs=[0, 0.2])),
        ("dash_sub_category", dict(group_by="Sub.Category")),
        ("dash_shipping_share", dict(ratio_of=["Shipping.Cost", "Sales"], bin_width=0.05)),
        ("dash_category", dict(group_by="Category")),
    ]
    problems = []
    for name, arguments in jobs:
        table, summary = tools.calculate_by_group(clean, **arguments)
        reconciled = "YES" in summary.split("Reconciliation:")[1]
        path, export_summary = tools.export_table(table, name, folder=FOLDER)
        file_ok = "Overall: YES" in export_summary
        print("\n" + name + ": " + str(len(table)) + " rows | reconciliation " + ("YES" if reconciled else "NO")
              + " | file check " + ("YES" if file_ok else "NO") + " | " + path)
        if not (reconciled and file_ok):
            problems.append(name)

    print("\n" + "=" * 40)
    print("DASHBOARD TABLES: " + ("ALL FOUR SAVED AND CHECKED" if not problems else "PROBLEMS IN " + ", ".join(problems)))


if __name__ == "__main__":
    main()
