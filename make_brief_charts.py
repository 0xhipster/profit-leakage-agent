"""Makes the two charts for the one-page brief, using the agent's own tools.

No internet, no API key, no cost. Charts are saved in output\\brief.

Run: python make_brief_charts.py superstore.csv
"""

import os
import sys

import tools

FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "brief")
DUP = ["Order.ID","Product.ID","Customer.ID","Order.Date","Sales","Quantity","Discount","Profit","Shipping.Cost"]
NAMES = {"up to and including 0.2": "20% or less (incl. none)", "above 0.2": "Over 20%"}
SRC = "Source: Global Superstore (Kaggle, fatihilhan), 51,290 order lines. Margin = total profit / total sales."
raw, _ = tools.load_data(sys.argv[1])
clean, rep = tools.clean_data(raw, drop_columns=["Market2","weeknum"], date_columns=["Order.Date","Ship.Date"], duplicate_columns=DUP)
def relabel(t):
    t = t.copy(); t["Discount band"] = t["Discount band"].map(NAMES); assert t["Discount band"].notna().all(); return t
t1, s1 = tools.calculate_by_group(clean, group_by="Discount", cutoffs=[0.2]); print(s1)
p, s = tools.make_bar_chart(relabel(t1), "Discount band", "margin_pct", "Over 20%", "Sales discounted over 20% earned a margin of -42.21%",
    "Profit margin by discount size, 2011 to 2014. 11,328 of 51,290 order lines are over 20%.", SRC, number_format="percent", name="brief_chart1_discount", folder=FOLDER); print(s)
t2, s2 = tools.calculate_by_group(clean, group_by="Discount", cutoffs=[0.2], filters=[{"column":"Sub.Category","equals":"Tables"}]); print(s2)
p, s = tools.make_bar_chart(relabel(t2), "Discount band", "margin_pct", "Over 20%", "Tables lines discounted over 20% earned a margin of -39.68%",
    "Tables only, 2011 to 2014. 467 of Tables' 861 order lines are over 20%.", SRC, number_format="percent", name="brief_chart2_tables", folder=FOLDER); print(s)
