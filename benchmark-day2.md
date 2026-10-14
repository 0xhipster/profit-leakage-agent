# Benchmark figures (Day 2, built by hand in Power BI)

Dataset: Global Superstore (Kaggle, fatihilhan). Report file: profit-leakage-benchmark.pbix
Units: currency not verified, so treated as "currency units". Sales values are whole numbers in the file.
The agent on Day 7 must reproduce every figure below exactly.

## Anchor numbers (whole dataset)
- Rows: 51,290
- Total Sales: 12,642,905
- Total Profit: 1,467,457.29
- Margin: 11.61% (Total Profit divided by Total Sales, after adding up)

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
| Band | Rows | Sales | Profit | Margin |
|---|---|---|---|---|
| None | 29,009 | 6,992,734 | 1,770,695.27 | 25.32% |
| Low (up to 20%) | 10,953 | 3,719,929 | 511,444.10 | 13.75% |
| High (over 20%) | 11,328 | 1,930,242 | -814,682.09 | -42.21% |

## Hypothesis status
- H1 Discount: supported at the 20% cutoff. High-discount rows lose money, low-discount rows make money. Association only.
- H2 Shipping: not tested yet.
- H3 Technology loses money: fails. Technology has the highest margin (13.99%).

## Data notes for the README
- Power BI's automatic type guess rounded Discount to 0 and 1. Fixed by setting types by hand. Check the distinct count (27), not the display format.
- Sales is stored without decimals in the source file.
- Power Query Min/Max lines were unreliable here (showed Sales max 999 and Quantity max 9). Check extremes by sorting.
- Market2 merges US and Canada into North America. Use Market.
- The record-count column (Chinese header) is constant 1. One row has Sales of 0.

## Still open
- Years covered (needed for "per year" in the headline)
- Does Order ID repeat across rows (confirms one row is one line item)
- Does Profit already include shipping cost (affects reading of H2)
- Kaggle licence
