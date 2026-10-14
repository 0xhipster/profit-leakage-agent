# Benchmark figures (Day 2 and Day 3, built by hand in Power BI)

Dataset: Global Superstore (Kaggle, fatihilhan). Report file: profit-leakage-benchmark.pbix
Units: currency not verified, so treated as "currency units". Sales values are whole numbers in the file.
The agent on Day 7 must reproduce every figure below exactly.

## Anchor numbers (whole dataset, unchanged after cleaning)
- Rows: 51,290
- Total Sales: 12,642,905
- Total Profit: 1,467,457.29
- Margin: 11.61% (Total Profit divided by Total Sales, after adding up)
- Duplicate rows: 0 (checked on Order.ID, Product.ID, Customer.ID, Order.Date, Sales, Quantity, Discount, Profit, Shipping.Cost)

## By Year (Year column, assumed to be the order year, not yet checked against Order.Date)
| Year | Sales | Profit | Rows |
|---|---|---|---|
| 2011 | 2,259,511 | 248,940.81 | 8,998 |
| 2012 | 2,677,493 | 307,415.28 | 10,962 |
| 2013 | 3,405,860 | 406,935.23 | 13,799 |
| 2014 | 4,300,041 | 504,165.97 | 17,531 |
The data covers 2011 to 2014. State findings "over four years", not "per year".

## By Category
| Category | Sales | Profit | Margin |
|---|---|---|---|
| Furniture | 4,110,884 | 285,204.72 | 6.94% |
| Office Supplies | 3,787,330 | 518,473.83 | 13.69% |
| Technology | 4,744,691 | 663,778.73 | 13.99% |

## By Market (Market column, 7 values)
| Market | Sales | Profit | Margin |
|---|---|---|---|
| Africa | 783,776 | 88,871.63 | 11.34% |
| APAC | 3,585,833 | 436,000.05 | 12.16% |
| Canada | 66,932 | 17,817.39 | 26.62% |
| EMEA | 806,184 | 43,897.97 | 5.45% |
| EU | 2,938,139 | 372,829.74 | 12.69% |
| LATAM | 2,164,687 | 221,643.49 | 10.24% |
| US | 2,297,354 | 286,397.02 | 12.47% |

## By Discount band
Cutoffs: None = 0, Low = above 0 up to and including 0.20, High = above 0.20.
Chosen after looking at profit by discount level, so the 20% line is partly fitted to this data.
| Band | Rows | Sales | Profit | Margin | Rows with Profit below 0 |
|---|---|---|---|---|---|
| None | 29,009 | 6,992,734 | 1,770,695.27 | 25.32% | 0 |
| Low (up to 20%) | 10,953 | 3,719,929 | 511,444.10 | 13.75% | 2,364 |
| High (over 20%) | 11,328 | 1,930,242 | -814,682.09 | -42.21% | 10,180 |
Total rows with Profit below 0: 12,544.

## By Shipping Share (Shipping.Cost divided by Sales, 5 point bins)
Each bin label is assumed to be the lower edge (0.05 means 5% up to under 10%). Not confirmed.
The one row with Sales of 0 has no share and sits in its own blank bin.
| Bin | Rows | Sales | Profit | Margin |
|---|---|---|---|---|
| blank (Sales = 0) | 1 | 0 | -1.11 | n/a |
| 0.00 | 7,183 | 1,888,992 | 229,063.85 | 12.13% |
| 0.05 | 22,000 | 5,413,328 | 629,207.03 | 11.62% |
| 0.10 | 11,637 | 2,883,603 | 332,023.50 | 11.51% |
| 0.15 | 5,284 | 1,257,096 | 140,442.59 | 11.17% |
| 0.20 | 2,456 | 582,396 | 53,462.33 | 9.18% |
| 0.25 | 1,364 | 311,184 | 38,217.27 | 12.28% |
| 0.30 | 769 | 175,974 | 26,149.81 | 14.86% |
| 0.35 | 378 | 74,551 | 9,131.25 | 12.25% |
| 0.40 | 157 | 42,983 | 7,626.63 | 17.74% |
| 0.45 | 44 | 10,716 | 2,050.47 | 19.13% |
| 0.50 | 14 | 1,905 | 116.59 | 6.12% |
| 0.55 | 3 | 177 | -32.94 | -18.61% |
Reconciliation (resolved Day 7): the lowest bin's Sales was misread as 1,888,892 in the first version of this table. The true value is 1,888,992, found by the agent's tool and confirmed by the column adding to 12,642,905. All 13 bins now add up to 51,290 rows, 12,642,905 sales and 1,467,457.27 profit (display rounding against 1,467,457.29).

## Hypothesis status
- H1 Discount: supported at the 20% cutoff. High-discount rows lose money, low-discount rows make money. 89.9% of High-band rows lose money, versus 0% of None-band rows. Association only.
- H2 Shipping: not supported. Every shipping-share bin with a meaningful number of rows makes money (margins 9.18% to 19.13%) and margin does not fall as the share rises. The only negative bin (0.55) has 3 rows.
- H3 Technology loses money: not supported. Technology has the highest margin (13.99%).

## Data notes for the README and limits line
- Power BI's automatic type guess rounded Discount to 0 and 1. Fixed by setting types by hand. Check the distinct count (27), not the display format.
- Sales is stored without decimals in the source file.
- Power Query Min/Max lines were unreliable here (showed Sales max 999 and Quantity max 9). Check extremes by sorting.
- Market2 merges US and Canada into North America. Use Market.
- One row has Sales of 0.
- Order.ID has 25,035 distinct values across 51,290 rows, so one row is one product line inside an order. Say "line items", not "orders".
- Profit appears to exclude shipping cost. The main evidence is the shipping table: margin does not fall as shipping share rises (12.13% in the lowest bin, 17.74% at 40 to 45%). If shipping were subtracted, margin should drop steadily as the share rises. Weaker supporting fact: no row without a discount loses money. This is evidence, not proof, because we cannot see how Profit was built. So H2 only says Profit is not lower where shipping is a bigger share of sales in this dataset.
- Public datasets like this are often clean or synthetic, so findings demonstrate a method, not real business facts.

## Cleaning done (Day 3)
- Dropped: the constant record-count column (Chinese header), Market2, weeknum. 24 columns remain.
- No duplicate rows, so no anchor numbers changed.

## Power BI state
- Measures: Total Sales, Total Profit, Margin, Row Count (COUNTROWS of the table), Loss Rows, Duplicate Rows.
- Calculated columns: Discount Band, Shipping Share.
- Bin group: Shipping Share (bins), size 0.05.
- Benchmark page tables: Category, Market, Discount level, Discount Band, Year, Shipping Share bins.

## Still open
- Shipping Share Sales column re-checked on Day 7: resolved (see above).
- Do bigger discounts raise Quantity? Test, do not assume.
- Is Year the same as the year of Order.Date?
- Kaggle licence (could not be read automatically, check the dataset page by hand).
- By-hand tables for Sub-Category and Segment are missing, so the agent's drill-downs on them cannot yet be validated.
- Does the sender expect Microsoft Copilot as well, and is Power BI required?
- Day 12 date: Sunday 18 October if days run back to back from Day 3 on Friday 9 October, Monday 19 October if one day is skipped.
