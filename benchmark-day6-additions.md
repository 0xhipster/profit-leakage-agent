# Benchmark additions (Day 6): by-hand Power BI tables

Built by hand in Power BI (profit-leakage-benchmark.pbix, report page 2 "Benchmark") and checked against the agent's output. Every row matched on all five measures. These are additions to benchmark-day3.md, which stays the main benchmark file.

Anchors (every table must add back to these): 51,290 rows, sales 12,642,905, profit 1,467,457.29, margin 11.61%, loss rows 12,544.

Columns: rows | sales | profit | margin % | loss rows. Profit is in currency units (not verified). Margin = total profit / total sales after adding up.

## Sub-Category (17 rows, lowest profit first)
| Sub-Category | rows | sales | profit | margin % | loss rows |
|---|---|---|---|---|---|
| Tables | 861 | 757,034 | -64,083.39 | -8.47 | 496 |
| Fasteners | 2,420 | 83,254 | 11,525.42 | 13.84 | 612 |
| Labels | 2,606 | 73,433 | 15,010.51 | 20.44 | 520 |
| Supplies | 2,425 | 243,090 | 22,583.26 | 9.29 | 589 |
| Envelopes | 2,435 | 170,926 | 29,601.12 | 17.32 | 555 |
| Furnishings | 3,170 | 385,609 | 46,967.43 | 12.18 | 804 |
| Art | 4,883 | 372,163 | 57,953.91 | 15.57 | 910 |
| Machines | 1,486 | 779,071 | 58,867.87 | 7.56 | 454 |
| Paper | 3,538 | 244,307 | 59,207.68 | 24.23 | 527 |
| Binders | 6,152 | 461,952 | 72,449.85 | 15.68 | 1,528 |
| Storage | 5,059 | 1,127,124 | 108,461.49 | 9.62 | 1,380 |
| Accessories | 3,075 | 749,307 | 129,626.31 | 17.30 | 656 |
| Chairs | 3,434 | 1,501,682 | 140,396.27 | 9.35 | 1,100 |
| Appliances | 1,755 | 1,011,081 | 141,680.59 | 14.01 | 382 |
| Bookcases | 2,411 | 1,466,559 | 161,924.42 | 11.04 | 717 |
| Phones | 3,357 | 1,706,874 | 216,717.01 | 12.70 | 789 |
| Copiers | 2,223 | 1,509,439 | 258,567.55 | 17.13 | 525 |

## Segment (3 rows)
| Segment | rows | sales | profit | margin % | loss rows |
|---|---|---|---|---|---|
| Home Office | 9,343 | 2,309,956 | 277,009.18 | 11.99 | 2,252 |
| Corporate | 15,429 | 3,824,808 | 441,208.33 | 11.54 | 3,771 |
| Consumer | 26,518 | 6,508,141 | 749,239.78 | 11.51 | 6,521 |
| Total | 51,290 | 12,642,905 | 1,467,457.29 | 11.61 | 12,544 |

## Region (13 rows, lowest profit first)
| Region | rows | sales | profit | margin % | loss rows |
|---|---|---|---|---|---|
| Canada | 384 | 66,932 | 17,817.39 | 26.62 | 0 |
| Southeast Asia | 3,129 | 884,438 | 17,852.33 | 2.02 | 1,668 |
| Caribbean | 1,690 | 324,281 | 34,571.32 | 10.66 | 435 |
| EMEA | 5,029 | 806,184 | 43,897.97 | 5.45 | 1,606 |
| Africa | 4,587 | 783,776 | 88,871.63 | 11.34 | 1,030 |
| East | 2,848 | 678,834 | 91,522.78 | 13.48 | 553 |
| West | 3,203 | 725,514 | 108,418.45 | 14.94 | 318 |
| Oceania | 3,487 | 1,100,207 | 120,089.11 | 10.92 | 1,059 |
| Central Asia | 2,048 | 752,839 | 132,480.19 | 17.60 | 273 |
| South | 6,645 | 1,600,960 | 140,355.77 | 8.77 | 1,688 |
| North Asia | 2,338 | 848,349 | 165,578.42 | 19.52 | 221 |
| North | 4,785 | 1,248,192 | 194,597.95 | 15.59 | 911 |
| Central | 11,117 | 2,822,399 | 311,403.98 | 11.03 | 2,782 |
| Total | 51,290 | 12,642,905 | 1,467,457.29 | 11.61 | 12,544 |

## Shipping Share table check
The 13 bins add to 12,642,905 sales, 51,290 rows and 1,467,457.27 profit (anchor 1,467,457.29, display rounding). The earlier 100 gap was a misreading. One line item has 0 sales (profit -1.11) and falls in the blank bin, because shipping cost divided by sales is undefined for it.
