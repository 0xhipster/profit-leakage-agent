"""Extra checks behind the brief. These are NOT done by the agent's five tools.

The agent's tools group and add up. They cannot compare the same product at
two discount levels, so those few numbers in the brief come from this script.
No internet, no API key, no cost. Plain pandas.

Run: python extra_checks.py superstore.csv
"""

import sys

import pandas as pd


def margin(rows):
    return rows["Profit"].sum() / rows["Sales"].sum() * 100


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = pd.read_csv(sys.argv[1], encoding="utf-8")
    df["heavy"] = df["Discount"] > 0.2          # over 20%
    print("Order lines:", f"{len(df):,}")

    # 1. Same products at both discount levels (answers "just bad products?")
    flags = df.groupby("Product.ID")["heavy"].agg(["min", "max"])
    both = flags[(flags["min"] == False) & (flags["max"] == True)].index  # noqa: E712
    same = df[df["Product.ID"].isin(both)]
    print("\n1. Products sold both at 20% or less and over 20%:", f"{len(both):,}", "of", f"{df['Product.ID'].nunique():,}")
    print("   their lines at 20% or less: margin", round(margin(same[~same.heavy]), 2))
    print("   their lines over 20%:       margin", round(margin(same[same.heavy]), 2))

    # 2. If every over-20% line disappeared (a bound on the volume risk, not a forecast)
    tables = df[df["Sub.Category"] == "Tables"]
    print("\n2. Tables profit now:", round(tables["Profit"].sum(), 2),
          "| without its over-20% lines:", round(tables[~tables.heavy]["Profit"].sum(), 2))
    print("   Whole store profit now:", round(df["Profit"].sum(), 2),
          "| without over-20% lines:", round(df[~df.heavy]["Profit"].sum(), 2))

    # 3. Units per order line by discount size (a lead on the parked volume question)
    df["size"] = pd.cut(df["Discount"], [-1, 0, 0.2, 1], labels=["none", "up to 20%", "over 20%"])
    print("\n3. Average units per order line:")
    print(df.groupby("size", observed=True)["Quantity"].mean().round(2).to_string())
    print("   (units per line only: this says nothing about the NUMBER of orders)")


if __name__ == "__main__":
    main()
