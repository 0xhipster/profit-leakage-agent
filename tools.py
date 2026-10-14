"""Tools for the profit leakage agent.

Each tool is plain code. Claude chooses which tool to call, but the
code does all the work and all the arithmetic.
"""

import os

import numpy as np
import pandas as pd


def load_data(path):
    """Tool 1: read a CSV file and describe what is in it.

    Reads the file exactly as it is. It does not clean or change anything.
    Works on any CSV, not only this dataset.

    Returns (table, summary). The table is kept by the agent for later
    tools. The summary is plain text that gets sent back to Claude. For
    number columns it also lists the lowest and highest value, so any
    cutoff Claude picks can be based on a range it has really seen.
    """
    table = pd.read_csv(path, encoding="utf-8")

    lines = []
    lines.append("File: " + str(path))
    lines.append("Rows: " + format(len(table), ","))
    lines.append("Columns: " + str(len(table.columns)))
    lines.append("")
    lines.append("Column name | type as read | missing values | distinct values | lowest | highest (number columns only)")
    for name in table.columns:
        column = table[name]
        line = (
            str(name)
            + " | "
            + str(column.dtype)
            + " | "
            + str(int(column.isna().sum()))
            + " | "
            + str(int(column.nunique()))
        )
        if pd.api.types.is_numeric_dtype(column) and not pd.api.types.is_bool_dtype(column) and column.notna().any():
            line += " | " + format(float(column.min()), ".10g") + " | " + format(float(column.max()), ".10g")
        lines.append(line)
    return table, "\n".join(lines)


def clean_data(table, drop_columns=None, date_columns=None, duplicate_columns=None):
    """Tool 2: return a cleaned copy of the table, plus a plain report.

    Claude chooses the arguments after reading the load summary, so this
    tool is not hard-coded to one dataset. The original table is never
    changed.

    - Columns with only one distinct value are always dropped (they carry
      no information).
    - drop_columns: extra columns to drop, by name.
    - date_columns: columns to convert from text to real dates.
    - duplicate_columns: columns used to spot duplicate rows. If not given,
      all columns are used. Duplicates are counted and removed.
    """
    drop_columns = drop_columns or []
    date_columns = date_columns or []
    cleaned = table.copy()
    report = []
    report.append("Rows before: " + format(len(cleaned), ","))
    report.append("Columns before: " + str(len(cleaned.columns)))

    constant = [c for c in cleaned.columns if cleaned[c].nunique() == 1]
    if constant:
        cleaned = cleaned.drop(columns=constant)
        report.append("Dropped constant columns: " + ", ".join(constant))

    missing_names = [c for c in drop_columns if c not in cleaned.columns and c not in constant]
    to_drop = [c for c in drop_columns if c in cleaned.columns]
    if to_drop:
        cleaned = cleaned.drop(columns=to_drop)
        report.append("Dropped requested columns: " + ", ".join(to_drop))
    if missing_names:
        report.append("Could not drop (not found or already dropped): " + ", ".join(missing_names))

    for name in date_columns:
        if name in cleaned.columns:
            cleaned[name] = pd.to_datetime(cleaned[name])
            report.append("Converted to dates: " + name)
        else:
            report.append("Could not convert to dates (not found): " + name)

    subset = duplicate_columns if duplicate_columns else None
    if subset:
        not_found = [c for c in subset if c not in cleaned.columns]
        if not_found:
            raise ValueError(
                "Duplicate check columns not found (or already dropped): " + ", ".join(str(c) for c in not_found)
                + ". Columns available now: " + ", ".join(str(c) for c in cleaned.columns)
            )
        for name in subset:
            if cleaned[name].nunique() == len(cleaned):
                raise ValueError(
                    "Column " + str(name) + " has a different value in every row, so it can never reveal a "
                    "duplicate. Choose columns that describe what a row contains (for example order, product, "
                    "customer, date and amounts), not a row number or other unique ID."
                )
    duplicates = int(cleaned.duplicated(subset=subset).sum())
    report.append("Duplicate rows found: " + str(duplicates))
    if duplicates > 0:
        cleaned = cleaned.drop_duplicates(subset=subset)
        report.append("Duplicate rows removed: " + str(duplicates))

    report.append("Rows after: " + format(len(cleaned), ","))
    report.append("Columns after: " + str(len(cleaned.columns)))
    return cleaned, "\n".join(report)


def _apply_filters(table, filters):
    """Keep only the rows that meet every condition. Returns (kept rows, plain note).

    Each condition is a dict with a column and exactly one of: equals (a
    value), above (a number, strictly greater) or at_most (a number, less
    than or equal). All conditions must hold. Nothing is dropped silently:
    the note says how many rows were kept out of how many.
    """
    if not isinstance(filters, (list, tuple)) or not filters:
        raise ValueError("filters must be a list of conditions, each with a column and one of equals, above, at_most.")
    kept = table
    parts = []
    for condition in filters:
        if not isinstance(condition, dict) or "column" not in condition:
            raise ValueError("Each filter needs a column and exactly one of equals, above, at_most.")
        column = condition["column"]
        if column not in kept.columns:
            raise ValueError(
                "Filter column not found: " + str(column) + ". Columns available: "
                + ", ".join(str(c) for c in kept.columns)
            )
        operators = [k for k in ("equals", "above", "at_most") if condition.get(k) is not None]
        if len(operators) != 1:
            raise ValueError("Each filter needs exactly one of equals, above, at_most (column " + str(column) + ").")
        operator = operators[0]
        value = condition[operator]
        series = kept[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            raise ValueError(
                "Filtering on a date column is not supported (" + str(column)
                + "). Use a year column, or group by a date part instead."
            )
        numeric = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
        if operator == "equals":
            if numeric:
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    raise ValueError("Column " + str(column) + " is numeric, so equals needs a number, not " + str(value) + ".")
                mask = series == number
                parts.append(str(column) + " equals " + format(number, "g"))
            else:
                mask = series.astype(str) == str(value)
                parts.append(str(column) + " equals " + str(value))
        else:
            if not numeric:
                raise ValueError(operator + " needs a number column, but " + str(column) + " is not numeric.")
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError(operator + " needs a number, not " + str(value) + ".")
            mask = (series > number) if operator == "above" else (series <= number)
            parts.append(str(column) + (" above " if operator == "above" else " at most ") + format(number, "g"))
        kept = kept[mask]
        if len(kept) == 0:
            hint = ""
            if not numeric and series.nunique() <= 30:
                hint = " Values in this column: " + ", ".join(str(v) for v in sorted(series.astype(str).unique())) + "."
            raise ValueError("The filter (" + " and ".join(parts) + ") leaves 0 rows." + hint)
    note = (
        "Filter applied: " + " and ".join(parts) + ". Rows kept: " + format(len(kept), ",") + " of " + format(len(table), ",")
        + "."
    )
    return kept, note


def calculate_by_group(table, group_by=None, sales_column="Sales", profit_column="Profit", cutoffs=None,
                       bin_width=None, ratio_of=None, date_part=None, filters=None):
    """Tool 3: add up sales and profit for each group, then work out margin.

    Claude chooses what to group by. The code does all the sums.
    Margin is total profit divided by total sales for the group, worked
    out after adding up (never an average of row margins).

    Also counts the rows in each group where profit is below 0 (loss_rows),
    works out the share of rows that lose money (loss_rate_pct = loss_rows
    divided by rows, times 100), and checks that the group totals add back up to the whole table, so
    nothing is lost or double counted.

    What to group by (use one of these):
    - group_by alone: each distinct value of one existing column.
    - group_by plus cutoffs: a number column put into bands first. Cutoffs
      is an increasing list. Each cutoff belongs to the band below it.
      Example: cutoffs [0, 0.2] gives three bands: up to and including 0,
      above 0 up to and including 0.2, and above 0.2.
    - group_by plus bin_width: a number column put into equal-width bins.
      Each bin includes its lower edge and excludes its upper edge (0.05
      gives 0 to under 0.05, 0.05 to under 0.1, and so on).
    - ratio_of [numerator, denominator] plus cutoffs or bin_width: the
      ratio of two columns per row (for example Shipping.Cost and Sales)
      is banded. Rows where the denominator is 0 or missing have no ratio.
      They are kept in their own group, never dropped. Ratios are rounded
      to 6 decimals before binning so values that sit exactly on an edge
      land in the same bin on every computer.
    - group_by (a date column) plus date_part ("year", "quarter" or
      "month"): the date is reduced to that part first.

    Any of the above can be combined with filters: a list of conditions,
    each a dict with a column and exactly one of equals (a value), above
    (a number) or at_most (a number). Only rows meeting every condition are
    used, the result says how many rows were kept out of how many, and the
    reconciliation is against the kept rows. Example: filters
    [{"column": "Sub.Category", "equals": "Tables"}] grouped by Discount
    bands shows what drives the losses inside Tables.

    The band edges are written in the result so a person can see exactly
    where the lines were drawn.

    Returns (result_table, summary). The summary is plain text for Claude
    and also shows the calculation that was run, so a person can verify it.
    """
    for name in (sales_column, profit_column):
        if name not in table.columns:
            raise ValueError("Column not found: " + str(name))
    filter_note = ""
    if filters:
        table, filter_note = _apply_filters(table, filters)
        filter_note += (
            " Sales " + format(table[sales_column].sum(), ",.0f") + ", profit " + format(table[profit_column].sum(), ",.2f")
            + " in the kept rows."
        )
    if cutoffs and bin_width:
        raise ValueError("Give cutoffs or bin_width, not both.")
    if ratio_of and date_part:
        raise ValueError("Give ratio_of or date_part, not both.")

    undefined_note = ""
    undefined_label = "undefined (denominator is 0 or missing)"
    if ratio_of:
        if not isinstance(ratio_of, (list, tuple)) or len(ratio_of) != 2:
            raise ValueError("ratio_of needs exactly two column names: [numerator, denominator].")
        numerator, denominator = ratio_of
        for name in (numerator, denominator):
            if name not in table.columns:
                raise ValueError("Column not found: " + str(name))
            if not pd.api.types.is_numeric_dtype(table[name]):
                raise ValueError("ratio_of needs number columns, but " + str(name) + " is not numeric.")
        if not cutoffs and not bin_width:
            raise ValueError("ratio_of needs cutoffs or bin_width, because a ratio is different in almost every row.")
        values = table[numerator] / table[denominator].where(table[denominator] != 0)
        values = values.round(6)
        source_label = str(numerator) + " / " + str(denominator)
        what = "ratio " + source_label
        count_undefined = int(values.isna().sum())
        undefined_note = (
            "Rows with no ratio (denominator is 0 or missing): " + str(count_undefined)
            + (". They are kept in their own group." if count_undefined else ".")
        )
    elif date_part:
        if group_by not in table.columns:
            raise ValueError("Column not found: " + str(group_by))
        if date_part not in ("year", "quarter", "month"):
            raise ValueError("date_part must be 'year', 'quarter' or 'month'.")
        if not pd.api.types.is_datetime64_any_dtype(table[group_by]):
            raise ValueError(
                str(group_by) + " is not a date column. Convert it first with clean_data (date_columns)."
            )
        dates = table[group_by]
        if date_part == "year":
            values = dates.dt.year
        elif date_part == "quarter":
            values = dates.dt.year.astype("Int64").astype(str) + " Q" + dates.dt.quarter.astype("Int64").astype(str)
        else:
            values = dates.dt.strftime("%Y-%m")
        source_label = str(group_by) + " " + date_part
        what = date_part + " of " + str(group_by)
        values = values.where(dates.notna())
    else:
        if not group_by:
            raise ValueError("Give group_by (a column name), or ratio_of with cutoffs or bin_width.")
        if group_by not in table.columns:
            raise ValueError("Column not found: " + str(group_by))
        values = table[group_by]
        source_label = str(group_by)
        what = str(group_by)

    label_column = source_label
    band_note = ""
    if cutoffs or bin_width:
        if not pd.api.types.is_numeric_dtype(values):
            raise ValueError("Cutoffs and bin_width need a number column, but " + source_label + " is not numeric.")
    if cutoffs:
        edges = [float(c) for c in cutoffs]
        if edges != sorted(set(edges)):
            raise ValueError("Cutoffs must be increasing numbers with no repeats.")
        names = ["up to and including " + format(edges[0], "g")]
        for low, high in zip(edges[:-1], edges[1:]):
            names.append("above " + format(low, "g") + " up to and including " + format(high, "g"))
        names.append("above " + format(edges[-1], "g"))
        label_column = source_label + " band"
        labels = pd.cut(values, bins=[float("-inf")] + edges + [float("inf")], labels=names, right=True).astype(object)
        band_note = " (banded at " + ", ".join(format(e, "g") for e in edges) + "; each cutoff belongs to the band below it)"
    elif bin_width:
        width = float(bin_width)
        if width <= 0:
            raise ValueError("bin_width must be a positive number.")
        label_column = source_label + " bin"
        steps = np.floor(values / width + 1e-9)
        labels = steps.map(
            lambda s: s if s != s else format(s * width, "g") + " to under " + format((s + 1) * width, "g")
        ).astype(object)
        band_note = " (equal bins of width " + format(width, "g") + "; each bin includes its lower edge and excludes its upper edge)"
    else:
        labels = values
    if ratio_of:
        labels = labels.where(labels.notna(), undefined_label)

    working = table.copy()
    working[label_column] = labels
    working = working.assign(_is_loss=(working[profit_column] < 0))
    grouped = working.groupby(label_column, dropna=False).agg(
        rows=(sales_column, "size"),
        sales=(sales_column, "sum"),
        profit=(profit_column, "sum"),
        loss_rows=("_is_loss", "sum"),
    )
    grouped["margin_pct"] = (grouped["profit"] / grouped["sales"] * 100).where(
        grouped["sales"] != 0
    )
    grouped["loss_rate_pct"] = grouped["loss_rows"] / grouped["rows"] * 100
    grouped = grouped.sort_values("profit").reset_index()

    total_rows = len(table)
    total_sales = table[sales_column].sum()
    total_profit = table[profit_column].sum()
    rows_match = int(grouped["rows"].sum()) == total_rows
    sales_match = abs(grouped["sales"].sum() - total_sales) < 0.5
    profit_match = abs(grouped["profit"].sum() - total_profit) < 0.005

    lines = []
    lines.append("Calculation run: group by " + what + band_note + ", sum " + sales_column + " and " + profit_column + ", margin = profit / sales * 100 (after adding up), loss rows = rows where " + profit_column + " is below 0, loss rate = loss rows / rows * 100")
    if filter_note:
        lines.append(filter_note)
    if undefined_note:
        lines.append(undefined_note)
    lines.append("Sorted by profit, lowest first.")
    lines.append("")
    lines.append(label_column + " | rows | sales | profit | margin % | loss rows | loss rate %")
    for i in range(len(grouped)):
        label = grouped[label_column].iloc[i]
        margin_value = grouped["margin_pct"].iloc[i]
        margin = "n/a" if margin_value != margin_value else format(margin_value, ".2f")
        lines.append(
            str(label) + " | " + format(int(grouped["rows"].iloc[i]), ",") + " | "
            + format(grouped["sales"].iloc[i], ",.0f") + " | "
            + format(grouped["profit"].iloc[i], ",.2f") + " | " + margin + " | "
            + format(int(grouped["loss_rows"].iloc[i]), ",") + " | "
            + format(grouped["loss_rate_pct"].iloc[i], ".1f")
        )
    lines.append("")
    lines.append(
        "Groups: " + str(len(grouped)) + ". Groups with profit below 0: " + str(int((grouped["profit"] < 0).sum()))
        + ". Groups with profit above 0: " + str(int((grouped["profit"] > 0).sum())) + "."
    )
    total_margin = "n/a" if total_sales == 0 else format(total_profit / total_sales * 100, ".2f")
    lines.append(
        "All rows together" + (" (after the filter)" if filter_note else "") + ": " + format(total_rows, ",") + " rows, sales "
        + format(total_sales, ",.0f") + ", profit " + format(total_profit, ",.2f") + ", margin " + total_margin + "%."
    )
    missing_sales = int(table[sales_column].isna().sum())
    missing_profit = int(table[profit_column].isna().sum())
    if missing_sales or missing_profit:
        lines.append(
            "WARNING: " + format(missing_sales, ",") + " rows have no " + sales_column + " value and " + format(missing_profit, ",")
            + " rows have no " + profit_column + " value. Rows with a missing value add nothing to that column's sum, so sales, profit and margin can be off. Report this."
        )
    lines.append("Columns of the saved table (use these exact names for charts and export): " + ", ".join(str(c) for c in grouped.columns))
    lines.append(
        "Reconciliation: group rows, sales and profit add back to the " + ("filtered rows" if filter_note else "whole table") + ": "
        + ("YES" if (rows_match and sales_match and profit_match) else "NO, DO NOT TRUST THESE NUMBERS")
    )
    return grouped, "\n".join(lines)


def export_table(table, name, folder="output"):
    """Tool 4: save a table as a CSV file, so Power BI can read it.

    Changes no numbers. What goes in is exactly what is written. After
    saving, the file is read back and compared with the table (row count,
    column names, and every value in every number column), so a person can
    see the file matches.

    - name: file name without the .csv ending. Only letters, digits,
      underscores and hyphens are allowed, so the file can only be saved
      inside the output folder.
    - folder: where to save. It is created if it does not exist.

    Returns (path, summary). The summary is plain text for Claude.
    """
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    if not name or any(character not in allowed for character in str(name)):
        raise ValueError(
            "Bad file name: " + str(name)
            + ". Use only letters, digits, underscores and hyphens."
        )

    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, str(name) + ".csv")
    replaced = os.path.exists(path)
    try:
        table.to_csv(path, index=False, encoding="utf-8")
    except OSError as problem:
        raise OSError(
            "Could not save " + path + ". If this file is open in another program (for example Excel), close it and run again. ("
            + str(problem) + ")"
        )

    check = pd.read_csv(path, encoding="utf-8")
    rows_match = len(check) == len(table)
    columns_match = list(check.columns) == [str(c) for c in table.columns]
    numbers_match = True
    number_lines = []
    for column in table.columns:
        if pd.api.types.is_numeric_dtype(table[column]) and not pd.api.types.is_bool_dtype(table[column]):
            if rows_match:
                differences = (table[column].to_numpy(dtype="float64") - check[column].to_numpy(dtype="float64"))
                biggest = float(abs(differences[~pd.isna(differences)]).max()) if len(differences) else 0.0
                same = biggest < 0.000001 and int(pd.isna(table[column]).sum()) == int(pd.isna(check[column]).sum())
            else:
                biggest = float("nan")
                same = False
            numbers_match = numbers_match and same
            number_lines.append(
                str(column) + " | " + format(biggest, ".6f") + " | " + ("YES" if same else "NO")
            )

    lines = []
    lines.append("Saved: " + path + (" (replaced an existing file)" if replaced else ""))
    lines.append("Rows written: " + format(len(table), ","))
    lines.append("Columns written: " + str(len(table.columns)) + " (" + ", ".join(str(c) for c in table.columns) + ")")
    lines.append("")
    lines.append("Read-back check: file read again and compared with the table")
    lines.append("Rows match: " + ("YES" if rows_match else "NO"))
    lines.append("Column names match: " + ("YES" if columns_match else "NO"))
    if number_lines:
        lines.append("Number column | biggest difference, value by value | match")
        lines.extend(number_lines)
    lines.append(
        "Overall: "
        + ("YES, the file matches the table" if (rows_match and columns_match and numbers_match) else "NO, DO NOT TRUST THIS FILE")
    )
    return path, "\n".join(lines)


def make_bar_chart(table, label_column, value_column, highlight, title, subtitle, source,
                   number_format="number", name="chart", folder="output", keep=None, keep_from="lowest"):
    """Tool 5: draw one sorted bar chart from a fixed template and save it as a PNG.

    Claude chooses which table and columns to chart, which single bar to
    highlight, and writes the title (a sentence stating the conclusion),
    the subtitle (what is measured) and the source line. The code does all
    the drawing, so every chart looks the same.

    The template: bars sorted with the highest value at the top, all gray
    except the one highlighted bar, value written at the end of each bar,
    no gridlines, no legend, one font. Values are taken straight from the
    table, never retyped or recalculated.

    The tool cannot judge whether the title is true. A person (or the
    final check) must compare the title with the plotted values listed in
    the summary.

    - keep / keep_from: optional. If a table has more than 15 rows, give keep
      (2 to 15) and keep_from ("lowest" or "highest") to draw only that many
      bars from one end. The summary says how many bars were left out, and the
      title must not claim more than is shown. The highlighted bar must be
      among the bars drawn.
    - number_format: "percent" (12.3%), "number" (1,234) or "decimal" (1,234.56).
    - name: file name without .png. Letters, digits, underscores, hyphens only.

    Returns (path, summary). The summary lists every plotted value, because
    Claude cannot see the picture, only this text.
    """
    import textwrap

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    formats = {
        "percent": lambda v: format(v, ".1f") + "%",
        "number": lambda v: format(v, ",.0f"),
        "decimal": lambda v: format(v, ",.2f"),
    }
    if number_format not in formats:
        raise ValueError("Unknown number_format: " + str(number_format) + ". Use percent, number or decimal.")
    for column in (label_column, value_column):
        if column not in table.columns:
            raise ValueError(
                "Column not found: " + str(column) + ". Columns in this table: "
                + ", ".join(str(c) for c in table.columns)
            )
    if str(value_column).endswith("_pct") and number_format == "number":
        raise ValueError(
            "Column " + str(value_column) + " holds percentages. Use number_format 'percent' (one decimal, with a % sign) "
            "or 'decimal' (two decimals). 'number' would round a value such as -42.21 to -42 and drop the % sign."
        )
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    if not name or any(character not in allowed for character in str(name)):
        raise ValueError("Bad file name: " + str(name) + ". Use only letters, digits, underscores and hyphens.")
    if not pd.api.types.is_numeric_dtype(table[value_column]):
        raise ValueError("Value column is not numeric: " + str(value_column))
    if table[value_column].isna().any():
        raise ValueError("Value column has missing values. Fix or remove them first, nothing is dropped silently.")

    data = table[[label_column, value_column]].copy()
    data[label_column] = data[label_column].astype(str)
    if data[label_column].duplicated().any():
        raise ValueError("Duplicate labels in " + str(label_column) + ". Each bar needs its own label.")
    total_bars = len(data)
    kept_note = ""
    if keep is not None:
        if keep_from not in ("lowest", "highest"):
            raise ValueError("keep_from must be 'lowest' or 'highest'.")
        if int(keep) < 2 or int(keep) > 15:
            raise ValueError("keep must be between 2 and 15.")
        data = data.sort_values(value_column, ascending=(keep_from == "lowest")).head(int(keep))
        kept_note = (
            "Only the " + str(len(data)) + " " + keep_from + " of " + str(total_bars)
            + " bars are drawn. The other " + str(total_bars - len(data)) + " are not shown."
        )
    if len(data) < 2:
        raise ValueError("A chart needs at least 2 bars. For one number, show the number instead.")
    if len(data) > 15:
        raise ValueError(
            "Too many bars (" + str(len(data)) + "). Use at most 15. Add keep (for example 10) and keep_from "
            "('lowest' or 'highest') to draw only some of them, or chart a table with fewer rows."
        )
    if str(highlight) not in list(data[label_column]):
        raise ValueError("Highlight not found among the bars to be drawn: " + str(highlight))

    data = data.sort_values(value_column, ascending=False).reset_index(drop=True)
    labels = list(data[label_column])
    values = [float(v) for v in data[value_column]]
    count = len(values)

    gray = "#8e8d87"
    accent = "#2a78d6"
    ink = "#1a1a19"
    muted = "#52514e"
    hairline = "#d9d8d3"

    title_lines = textwrap.wrap(str(title), 62)
    subtitle_lines = textwrap.wrap(str(subtitle), 95)
    source_lines = textwrap.wrap(str(source), 115)
    width = 7.5
    header = 0.25 + 0.30 * len(title_lines) + 0.22 * len(subtitle_lines) + 0.15
    footer = 0.20 + 0.16 * len(source_lines)
    plot_height = 0.42 * count + 0.2
    height = header + plot_height + footer

    figure = plt.figure(figsize=(width, height), dpi=200, facecolor="white")
    longest = max(len(label) for label in labels)
    left = min(0.40, 0.04 + 0.0125 * longest)
    axes = figure.add_axes([left, footer / height, 0.97 - left, plot_height / height])
    axes.set_facecolor("white")

    positions = list(range(count))[::-1]
    colors = [accent if label == str(highlight) else gray for label in labels]
    axes.barh(positions, values, height=0.5, color=colors, linewidth=0)

    low = min(0.0, min(values))
    high = max(0.0, max(values))
    span = (high - low) or 1.0
    axes.set_xlim(low - (0.20 * span if low < 0 else 0), high + (0.20 * span if high > 0 else 0))
    axes.set_ylim(-0.6, count - 0.4)
    axes.axvline(0, color=hairline, linewidth=1)
    for position, label, value in zip(positions, labels, values):
        is_highlight = label == str(highlight)
        offset = 0.015 * span
        axes.text(
            value + (offset if value >= 0 else -offset), position, formats[number_format](value),
            va="center", ha="left" if value >= 0 else "right",
            fontsize=10, color=ink, fontweight="bold" if is_highlight else "normal",
        )
    axes.set_yticks(positions)
    axes.set_yticklabels(labels, fontsize=10, color=ink)
    axes.tick_params(axis="y", length=0, pad=6)
    axes.set_xticks([])
    for side in ("top", "right", "bottom", "left"):
        axes.spines[side].set_visible(False)

    top = 1 - 0.25 / height
    for line in title_lines:
        figure.text(0.03, top, line, fontsize=14, fontweight="bold", color=ink, va="top", ha="left")
        top -= 0.30 / height
    top -= 0.03 / height
    for line in subtitle_lines:
        figure.text(0.03, top, line, fontsize=9.5, color=muted, va="top", ha="left")
        top -= 0.22 / height
    bottom = (0.10 + 0.16 * (len(source_lines) - 1)) / height
    for line in source_lines:
        figure.text(0.03, bottom, line, fontsize=8, color=muted, va="bottom", ha="left")
        bottom -= 0.16 / height

    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, str(name) + ".png")
    replaced = os.path.exists(path)
    try:
        figure.savefig(path, facecolor="white")
    except OSError as problem:
        plt.close(figure)
        raise OSError(
            "Could not save " + path + ". If this picture is open in another program, close it and run again. ("
            + str(problem) + ")"
        )
    plt.close(figure)

    lines = []
    lines.append("Chart saved: " + path + (" (replaced an existing file)" if replaced else ""))
    lines.append("Template: sorted bars, highest at top, gray with one highlighted bar")
    lines.append("Title as drawn: " + str(title))
    lines.append("Subtitle as drawn: " + str(subtitle))
    lines.append("Source line as drawn: " + str(source))
    lines.append("Values plotted come straight from column " + str(value_column) + " of the table. Nothing was recalculated.")
    lines.append("Highlighted bar: " + str(highlight))
    if kept_note:
        lines.append(kept_note)
    lines.append("")
    lines.append("Bars from top to bottom: label | value as written on the chart")
    for label, value in zip(labels, values):
        lines.append(label + " | " + formats[number_format](value))
    return path, "\n".join(lines)
