# Sources: creative-goods HS continuity dataset

Access date for all files: 2026-11-18. Raw files are kept unchanged in `data/raw/hs/`. Outputs are rebuilt with
`python scripts/build_continuity.py`.

## 1. UNCTAD creative-goods definition (UNCTADstat)

Index page: https://unctadstat.unctad.org/EN/Classifications.html ("Creative product groupings and composition").
UNCTAD publishes one official list for each HS edition, so each edition is read from its own list. No list was
converted from another edition. The PDF footers say "Generation date: 09 September 2026".

| HS edition | File (Excel; a PDF with the same name is also downloaded) | SHA-256 (xls) |
|---|---|---|
| groups only | https://unctadstat.unctad.org/EN/Classifications/DimCreativeProducts_Creatives_Hierarchy.xls | ef19f6ba37d5ab2a96d51c9de176dad6a9f81f8a7784d6423e66bdeba0b50426 |
| HS 2002 | https://unctadstat.unctad.org/EN/Classifications/DimHS2002Products_Creatives_Hierarchy.xls | 7cbe69d6ebd7239f0c4f875bfa26d5d6223b39e30a2b6f64f505229f91224cc0 |
| HS 2007 | https://unctadstat.unctad.org/EN/Classifications/DimHS2007Products_Creatives_Hierarchy.xls | 1360a8fa934280b71d07a4ee6c28a83609b22687f63d15c71f22eca420330377 |
| HS 2012 | https://unctadstat.unctad.org/EN/Classifications/DimHS2012Products_Creatives_Hierarchy.xls | e3799b3be95a48e7be7fd1462980fea206642f6ad3a66c5249a37702df236443 |
| HS 2017 | https://unctadstat.unctad.org/EN/Classifications/DimHS2017Products_Creatives_Hierarchy.xls | cb947312cd9a2cddb693428be868795cdbf82ef8b74456a191abfe8d1af3868b |
| HS 2022 | https://unctadstat.unctad.org/EN/Classifications/DimHS2022Products_Creatives_Hierarchy.xls | e91af950f23d23f1cdaae397a6eb347ac4f8d3ef56ce98c2fe14712d6c94ab79 |

Category labels in the panel table come from the groups file. The per-edition files label CER060 "Software, video games,
computer and web services". The groups file labels it "Software, video games and recorded media", and the panel uses
this label. `creative_hs_codes.csv` keeps the label exactly as each per-edition file gives it.

## 2. HS correlation tables (UNSD)

Index page: https://unstats.un.org/unsd/classifications/Econ

| Pair | URL | Sheet used |
|---|---|---|
| HS2002→HS2007 | https://unstats.un.org/unsd/classifications/Econ/tables/HS%202007%20to%20HS%202002%20Correlation%20and%20conversion%20tables.xls | Correlation Tables |
| HS2007→HS2012 | https://unstats.un.org/unsd/classifications/Econ/tables/HS%202012%20to%20HS%202007%20Correlation%20and%20conversion%20tables.xls | Correlation HS2012-HS2007 |
| HS2012→HS2017 | https://unstats.un.org/unsd/classifications/Econ/tables/HS2017toHS2012ConversionAndCorrelationTables.xlsx | Correlation HS17-HS12 |
| HS2017→HS2022 | https://unstats.un.org/unsd/classifications/Econ/tables/HS2022toHS2017ConversionAndCorrelationTables.xlsx | HS2022-HS2017 Correlations |

Every creative code was found on the source side of its correlation table, so the dataset has no `not_in_table` cases.

Checked and not used: https://unctad.org/system/files/official-document/ditcted2024d2_en.pdf. This is a report on
ocean-related measures in SIDS' NDCs and contains no creative-goods HS list.

## 3. Method

For each creative HS6 code in edition A, the script takes every edition-B code linked to it in the full UNSD
correlation table, including links to non-creative codes. It also takes every edition-A code linked to those
edition-B codes. Each code is then classified as one of:

- `unchanged_1:1`: the code has one link, the link is exclusive, and the number is the same.
- `renumbered_1:1`: the code has one exclusive link, but the number is different.
- `split_1:n`: the code goes to several edition-B codes, and each of them comes only from this code.
- `merged_n:1`: the code goes to one edition-B code that also receives other edition-A codes.
- `complex_n:m`: any other pattern.

These classes match UNSD's own relationship labels. UNSD writes them from the newer edition's side, so its `n:1` is
`split_1:n` here.

`creative_hs_continuity.csv` adds two aggregates, `CER000` (all creative goods) and `CER020` (the sum of CER021 to
CER027), and fills empty relationship/category cells with 0. `creative_hs_code_links.csv` gives per-code detail. Its
column `code_persists` shows whether the edition-A code still exists in edition B. Its column `targets_in_next_list`
shows whether UNCTAD's edition-B list includes the linked codes, in the same category or in another one.

## 4. Caveats

1. The counts are counts of codes, not trade values. A `complex_n:m` code may lose only a very small part of its
   content. In HS2022 most complex cases come from "ex" links to new heading 85.49 (electrical and electronic waste)
   and to 85.24 (flat-panel display modules), for example 9504xx and 8523xx. In 18 of the 20 HS2017→HS2022 complex
   cases the code number still exists in HS2022. Without trade weights, these counts overstate how much was
   actually disrupted.
2. The relationship describes the HS nomenclature, not UNCTAD's decisions. UNCTAD's lists also change between
   editions: they grow from 195 codes (HS2002) to 230 codes (HS2022). In HS2022, UNCTAD split 9701–9703 by age and
   moved the parts over 100 years old (970121, 970122, 970129, 970210, 970310) from CER040 to CER070. Earlier,
   950450 (video-game consoles) was in CER060 and its HS2007 parent 950490 was in CER025. See `targets_in_next_list`.
3. Correlation tables for 1:n and n:m links do not say what share of the content goes to each code, so the
   classification is structural only.
4. HS1992 and HS1996 lists exist on the same UNCTADstat page but are out of scope.
5. The UNCTADstat files are live downloads (generated 2026-09-09) and could be revised. Check the SHA-256 values
   above before reusing them.
