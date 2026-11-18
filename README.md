# Who is missing from creative economy statistics?

An interactive dashboard on world trade in creative goods (2002–2024) and on the gaps in the data behind it.

**Live page:** https://xiaoxiaoshikui.github.io/creative-goods-data-gaps/

## What it shows

1. **The market.** Creative goods exports by developed economies, developing economies excluding China, and China.
2. **Where.** A world map by economy, category and year, as US$ or as a share of the economy's merchandise exports.
3. **What.** The category mix of creative goods exports for the world, developed and developing economies, LDCs and SIDS.
4. **Who is missing.** How many years each economy has no published value, compared by group (LDC, SIDS, LLDC, other) and by region.
5. **The definition moves.** How UNCTAD's list of creative HS codes maps across the HS 2002, 2007, 2012, 2017 and 2022 revisions.
6. **What this means** for statistical offices and for creative-economy indicators.

Main findings (data accessed 18 November 2026):

- **Missing years.** Least developed countries have no published value for 24% of years between 2002 and 2023. Economies outside the LDC, SIDS and LLDC groups miss 8%.
- **No 2024 value yet.** 55% of LDCs have no 2024 value, against 20% of other economies.
- **HS 2022 revision.** 32 of 213 creative HS codes (15%) were not kept one-to-one. This includes every code for video games, recorded media and toys.

## Data

| Source | Use |
|---|---|
| [UNCTADstat, Creative goods: value](https://unctadstat.unctad.org/datacentre/dataviewer/US.CreativeGoodsValue) (bulk download) | Exports to the world by economy, category and year |
| [UN M49](https://unstats.un.org/unsd/methodology/m49/overview/) | Regions and LDC, LLDC and SIDS membership |
| [UNCTADstat creative product groupings](https://unctadstat.unctad.org/EN/Classifications.html) | The creative-goods HS list for each HS edition |
| [UNSD HS correlation tables](https://unstats.un.org/unsd/classifications/Econ/) | Code links between consecutive HS editions |

The full source list, file checksums and caveats are in [`data/hs/SOURCES.md`](data/hs/SOURCES.md).

## Reproduce

```bash
pip install -r requirements.txt
bash scripts/download.sh            # about 335 MB download; the CSV is about 4 GB once extracted
python scripts/build_continuity.py  # writes data/hs/*.csv
python scripts/build_data.py        # writes docs/data/dashboard.json and docs/data/coverage.csv
python -m http.server -d docs 8000  # open http://localhost:8000
```

The page is static: one HTML file and Plotly.js, with no server code. GitHub Pages serves it from `docs/`.

## Caveats

- **A missing value is not zero trade.** It means that UNCTADstat publishes no figure for that economy and year.
- **Historical entities are excluded,** for example Netherlands Antilles and Serbia and Montenegro. Economies created after 2002 are counted from their first year.
- **HS changes are counted by code, not by trade value.** Many HS 2022 "complex" cases are small partial links to new headings, and in most of them the original code still exists.

## Author

Yunxiang Guo, November 2026. This is an independent analysis of public data, not an official publication of any organization.
