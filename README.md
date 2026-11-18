# Who is missing from creative economy statistics?

An interactive dashboard on world trade in creative goods (2002–2024) and on the gaps in the data behind it.

**Live page:** https://xiaoxiaoshikui.github.io/creative-goods-data-gaps/

## What it shows

1. **Who is missing.** For each economy, the share of years from 2002 to 2023 with no published creative-goods export value, by group (LDC, SIDS, LLDC, other), with bootstrap intervals and a permutation test.
2. **The gaps have widened.** Economies with no published value per year.
3. **Where.** A map of years missing (small island States as dots) and of export values by category and year.
4. **The definition moves.** How UNCTAD's list of creative HS codes maps across HS 2002, 2007, 2012, 2017 and 2022, separating real splits and merges from partial links where the code continues.
5. **What the available data show.** Market trend and category mix.
6. **What this means** for creative economy measurement.

Main findings (version 1.1, data accessed 18 November 2026):

- **Missing years.** Least developed countries have no published value for 36% of years from 2002 to 2023 on average, against 10% for economies outside the LDC, SIDS and LLDC groups. The difference is 26 percentage points (95% bootstrap interval 14–37; permutation p < 0.001).
- **Not listed at all.** Nine sovereign States, four of them LDCs (Chad, Haiti, Somalia, South Sudan), appear only as trading partners and never as reporters.
- **Widening.** Economies with no published value rose from 29 in 2017 to 45 in 2023.
- **HS 2022.** 31 of 213 creative codes were not kept one-to-one. For 18 of them the code continues with only a partial link to a new heading, so 13 codes (6%) changed in substance.

A companion page, [Generative AI and creative work](https://xiaoxiaoshikui.github.io/creative-goods-data-gaps/ai/), looks at which creative occupations are exposed to generative AI and tests an LLM-assisted occupation crosswalk against the official one.

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
bash scripts/download.sh             # about 335 MB download; the CSV is about 4 GB once extracted
python3 scripts/build_continuity.py  # writes data/hs/*.csv
python3 scripts/build_data.py        # writes docs/data/dashboard.json and docs/data/coverage.csv
python3 -m http.server -d docs 8000  # open http://localhost:8000
```

The page is static: one HTML file and Plotly.js, with no server code. GitHub Pages serves it from `docs/`.

## Caveats

- **A missing value is not zero trade.** It means that UNCTADstat publishes no figure for that economy and year.
- **What counts as missing.** A year is missing when UNCTADstat publishes no value (marked "Not publishable", empty, or no row). Rows marked "Not applicable" are excluded. Former codes are joined to current ones (Sudan before 2012, Indonesia 2002); entities that no longer exist are excluded.
- **Group totals are estimates.** UNCTAD's totals include estimates for some economies that have no published value.
- **HS changes are counted by code, not by trade value.** Partial links where the code continues are shown separately from real splits and merges.
- **Source checksums** are in `data/CHECKSUMS.sha256`; `scripts/download.sh` warns if UNCTAD has revised the file.

## Licence

Code: MIT. Derived tables: CC BY 4.0. Source data remain subject to the providers' terms of use.

## How to cite

Guo, Y. (2026). *Who is missing from creative economy statistics?* Interactive dashboard, version 1.1. https://xiaoxiaoshikui.github.io/creative-goods-data-gaps/

## Author

Yunxiang Guo, November 2026. This is an independent analysis of public data, not an official publication of any organization.
