#!/usr/bin/env bash
# Download the public source data into data/raw/. Requires curl and Python with py7zr, pandas, lxml.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw/hs/unctadstat data/raw/hs/unsd

# 1. UNCTADstat bulk file: Creative goods, value (7-zip archive, ~335 MB; ~4 GB CSV once extracted)
curl -L -o data/raw/US_CreativeGoodsValue.7z \
  "https://unctadstat-api.unctad.org/bulkdownload/US.CreativeGoodsValue/US_CreativeGoodsValue"
python -c "import py7zr; py7zr.SevenZipFile('data/raw/US_CreativeGoodsValue.7z').extractall('data/raw')"

# 2. UN M49 country groups
curl -L -A "Mozilla/5.0" -o data/raw/m49_overview.html "https://unstats.un.org/unsd/methodology/m49/overview/"
python -c "import pandas as pd; pd.read_html('data/raw/m49_overview.html', attrs={'id':'downloadTableEN'})[0].to_csv('data/raw/m49.csv', index=False)"

# 3. UNCTAD creative-goods HS lists, one per HS edition
curl -L -o data/raw/hs/unctadstat/DimCreativeProducts_Creatives_Hierarchy.xls "https://unctadstat.unctad.org/EN/Classifications/DimCreativeProducts_Creatives_Hierarchy.xls"
for v in 2002 2007 2012 2017 2022; do
  curl -L -o "data/raw/hs/unctadstat/DimHS${v}Products_Creatives_Hierarchy.xls" \
    "https://unctadstat.unctad.org/EN/Classifications/DimHS${v}Products_Creatives_Hierarchy.xls"
done
# 4. UNSD HS correlation tables for consecutive editions
U=https://unstats.un.org/unsd/classifications/Econ/tables
curl -L -o data/raw/hs/unsd/HS_2007_to_HS_2002_Correlation_and_conversion_tables.xls "$U/HS%202007%20to%20HS%202002%20Correlation%20and%20conversion%20tables.xls"
curl -L -o data/raw/hs/unsd/HS_2012_to_HS_2007_Correlation_and_conversion_tables.xls "$U/HS%202012%20to%20HS%202007%20Correlation%20and%20conversion%20tables.xls"
curl -L -o data/raw/hs/unsd/HS2017toHS2012ConversionAndCorrelationTables.xlsx "$U/HS2017toHS2012ConversionAndCorrelationTables.xlsx"
curl -L -o data/raw/hs/unsd/HS2022toHS2017ConversionAndCorrelationTables.xlsx "$U/HS2022toHS2017ConversionAndCorrelationTables.xlsx"
echo "Done. Next: python scripts/build_continuity.py && python scripts/build_data.py"
