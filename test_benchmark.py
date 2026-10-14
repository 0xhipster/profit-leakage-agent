"""Free check: do the tools reproduce every by-hand Power BI benchmark table?

No internet, no API key, no cost. The expected figures are read straight out
of benchmark-day3.md and benchmark-day6-additions.md (nothing is retyped).

Run: python test_benchmark.py superstore.csv
"""

import os
import re
import sys

import tools

DUPLICATES = ["Order.ID", "Product.ID", "Customer.ID", "Order.Date", "Sales", "Quantity", "Discount", "Profit", "Shipping.Cost"]


def number(text):
    text = text.replace(",", "").replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def read_tables(path):
    """Return {section heading: [rows]} where a row is a list of cell texts."""
    sections = {}
    current = None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current and line.startswith("|") and not re.match(r"^\|[-| ]+\|$", line):
            sections[current].append([c.strip() for c in line.strip("|").split("|")])
    return sections


def check(name, result, expected, columns, problems):
    """expected: {label: {column: value}}. columns: {column: tolerance}."""
    got = {}
    label_column = result.columns[0]
    for i in range(len(result)):
        got[str(result[label_column].iloc[i])] = {c: result[c].iloc[i] for c in result.columns[1:]}
    bad = []
    for label, wanted in expected.items():
        if label not in got:
            bad.append(label + ": group missing in tool output")
            continue
        for column, tolerance in columns.items():
            if column not in wanted or wanted[column] is None:
                continue
            have = got[label][column]
            if abs(float(have) - wanted[column]) > tolerance:
                bad.append(label + " " + column + ": tool " + format(float(have), ",.4f") + ", benchmark " + format(wanted[column], ",.4f"))
    for label, wanted in expected.items():
        if label in got and wanted.get("rows") and wanted.get("loss_rows") is not None:
            want_rate = wanted["loss_rows"] / wanted["rows"] * 100
            if abs(float(got[label]["loss_rate_pct"]) - want_rate) > 0.0001:
                bad.append(label + " loss_rate_pct: tool " + format(float(got[label]["loss_rate_pct"]), ".4f") + ", benchmark " + format(want_rate, ".4f"))
    extra = [g for g in got if g not in expected]
    if extra:
        bad.append("groups in tool output but not in benchmark: " + ", ".join(extra))
    print(("PASS  " if not bad else "FAIL  ") + name + " (" + str(len(expected)) + " groups)")
    for b in bad:
        print("      " + b)
        problems.append(name + ": " + b)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data_path = sys.argv[1]
    folder = os.path.dirname(os.path.abspath(data_path))
    day3 = read_tables(os.path.join(folder, "benchmark-day3.md"))
    day6 = read_tables(os.path.join(folder, "benchmark-day6-additions.md"))
    problems = []

    raw, _ = tools.load_data(data_path)
    clean, _ = tools.clean_data(raw, drop_columns=["Market2", "weeknum"], date_columns=["Order.Date", "Ship.Date"],
                                duplicate_columns=DUPLICATES)

    def table_of(sections, heading_start, skip_total=True):
        for heading, rows in sections.items():
            if heading.startswith(heading_start):
                return rows[1:]
        raise KeyError(heading_start)

    tol = {"rows": 0.5, "sales": 0.5, "profit": 0.006, "margin_pct": 0.006, "loss_rows": 0.5}

    def build(rows, order):
        out = {}
        for r in rows:
            if r[0] == "Total":
                continue
            out[r[0]] = {c: number(r[i]) for c, i in order.items() if i < len(r)}
        return out

    # Day 3 tables: label | sales | profit | margin (Category, Market), label | rows | sales | profit (Year)
    result, _ = tools.calculate_by_group(clean, "Category")
    check("Category", result, build(table_of(day3, "By Category"), {"sales": 1, "profit": 2, "margin_pct": 3}), tol, problems)
    result, _ = tools.calculate_by_group(clean, "Market")
    check("Market", result, build(table_of(day3, "By Market"), {"sales": 1, "profit": 2, "margin_pct": 3}), tol, problems)
    result, _ = tools.calculate_by_group(clean, "Year")
    check("Year (Year column)", result, build(table_of(day3, "By Year"), {"sales": 1, "profit": 2, "rows": 3}), tol, problems)

    # Year column against the year of Order.Date: same expected figures.
    result, _ = tools.calculate_by_group(clean, "Order.Date", date_part="year")
    check("Year (year of Order.Date)", result, build(table_of(day3, "By Year"), {"sales": 1, "profit": 2, "rows": 3}), tol, problems)

    # Discount band at cutoffs 0 and 0.2
    result, _ = tools.calculate_by_group(clean, "Discount", cutoffs=[0, 0.2])
    names = {"None": "up to and including 0", "Low (up to 20%)": "above 0 up to and including 0.2", "High (over 20%)": "above 0.2"}
    wanted = {}
    for r in table_of(day3, "By Discount band"):
        wanted[names[r[0]]] = {"rows": number(r[1]), "sales": number(r[2]), "profit": number(r[3]), "margin_pct": number(r[4]), "loss_rows": number(r[5])}
    check("Discount band (cutoffs 0 and 0.2)", result, wanted, tol, problems)
    wanted_discount = wanted
    high = result[result.iloc[:, 0] == "above 0.2"]["loss_rate_pct"].iloc[0]
    none = result[result.iloc[:, 0] == "up to and including 0"]["loss_rate_pct"].iloc[0]
    ok = format(high, ".1f") == "89.9" and none == 0
    print(("PASS  " if ok else "FAIL  ") + "Loss rate: High band " + format(high, ".1f") + "% (benchmark text says 89.9%), None band " + format(none, ".1f") + "% (says 0%)")
    if not ok:
        problems.append("Loss rate for the discount bands does not match the 89.9% and 0% in benchmark-day3.md")

    # Shipping share, 5 point bins. Bin labels in the benchmark are lower edges.
    result, summary = tools.calculate_by_group(clean, ratio_of=["Shipping.Cost", "Sales"], bin_width=0.05)
    wanted = {}
    for r in table_of(day3, "By Shipping Share"):
        if r[0].startswith("blank"):
            key = "undefined (denominator is 0 or missing)"
        else:
            low = float(r[0])
            key = format(low, "g") + " to under " + format(round(low + 0.05, 2), "g")
        wanted[key] = {"rows": number(r[1]), "sales": number(r[2]), "profit": number(r[3]), "margin_pct": number(r[4])}
    check("Shipping Share bins (ratio, width 0.05)", result, wanted, tol, problems)
    total_sales = result["sales"].sum()
    print("      bins add up to sales " + format(total_sales, ",.0f") + ", rows " + format(int(result["rows"].sum()), ",")
          + ", and the tool's own reconciliation says: " + summary.split("whole table: ")[1].splitlines()[0])

    # Day 6 additions: label | rows | sales | profit | margin | loss rows
    order = {"rows": 1, "sales": 2, "profit": 3, "margin_pct": 4, "loss_rows": 5}
    for heading, column in (("Sub-Category", "Sub.Category"), ("Segment", "Segment"), ("Region", "Region")):
        result, summary = tools.calculate_by_group(clean, column)
        expected = build(table_of(day6, heading), order)
        check(heading, result, expected, tol, problems)
        want = "Groups: " + str(len(expected)) + ". Groups with profit below 0: " + str(sum(1 for v in expected.values() if v["profit"] < 0))
        if want not in summary:
            problems.append(heading + ": the summary does not state the group counts as the benchmark implies (" + want + ")")
            print("FAIL  " + heading + " group counts: expected the line '" + want + "'")
        else:
            print("PASS  " + heading + " group counts (" + want + ")")

    # Filters: the groups inside a filter must add back to the by-hand totals of the same rows.
    def filter_totals(name, filters, group_by, target):
        result, summary = tools.calculate_by_group(clean, group_by, filters=filters)
        have = {
            "rows": float(result["rows"].sum()), "sales": float(result["sales"].sum()),
            "profit": float(result["profit"].sum()), "loss_rows": float(result["loss_rows"].sum()),
        }
        bad = [
            c + ": tool " + format(have[c], ",.2f") + ", benchmark " + format(target[c], ",.2f")
            for c in have if abs(have[c] - target[c]) > (0.006 if c == "profit" else 0.5)
        ]
        if "add back to the filtered rows: YES" not in summary:
            bad.append("the tool's own reconciliation line is not YES")
        print(("PASS  " if not bad else "FAIL  ") + "Filter: " + name)
        for line in bad:
            print("      " + line)
            problems.append("Filter " + name + ": " + line)

    high = wanted_discount["above 0.2"]
    low = wanted_discount["above 0 up to and including 0.2"]
    tables = build(table_of(day6, "Sub-Category"), order)["Tables"]
    filter_totals("Discount above 0.2, grouped by Category, adds to the High band",
                  [{"column": "Discount", "above": 0.2}], "Category", high)
    filter_totals("Discount above 0 and at most 0.2 (two conditions), grouped by Year, adds to the Low band",
                  [{"column": "Discount", "above": 0}, {"column": "Discount", "at_most": 0.2}], "Year", low)
    filter_totals("Sub.Category equals Tables, grouped by Region, adds to the Tables row",
                  [{"column": "Sub.Category", "equals": "Tables"}], "Region", tables)

    print("\n" + "=" * 40)
    print("BENCHMARK RESULT: " + ("ALL TABLES MATCH" if not problems else "PROBLEMS FOUND"))
    for p in problems:
        print(" - " + p)


if __name__ == "__main__":
    main()
