"""Build HS-revision continuity statistics for UNCTAD's creative-goods definition.

Inputs (downloaded verbatim, see data/hs/SOURCES.md):
  data/raw/hs/unctadstat/DimHS{2002,2007,2012,2017,2022}Products_Creatives_Hierarchy.xls
      UNCTADstat creative-goods groupings, one official list per HS edition.
  data/raw/hs/unsd/*  UNSD HS correlation tables for consecutive editions.

Outputs (data/hs/):
  creative_hs_codes.csv          every (HS edition, category, HS6 code) in UNCTAD's lists
  creative_hs_continuity.csv     relationship counts per edition pair x category (required panel data)
  creative_hs_code_links.csv     per-code detail: relationship, linked codes, and whether the
                                 linked codes are in UNCTAD's list for the next edition

Relationship is computed from the full UNSD correlation (all HS6 codes, not just creative ones):
  unchanged_1:1  code maps to exactly one code, which maps back only to it, same number
  renumbered_1:1 as above, different number
  split_1:n      code maps to >1 codes, each of which comes only from this code
  merged_n:1     code maps to exactly 1 code, which also receives other codes
  complex_n:m    anything else (many-to-many component)
  not_in_table   code not found on the source side of the correlation table

Run:  python scripts/build_continuity.py
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "data" / "raw" / "hs"
OUT = ROOT / "data" / "hs"
OUT.mkdir(exist_ok=True)

VERSIONS = ["HS2002", "HS2007", "HS2012", "HS2017", "HS2022"]

# (newer, older) -> (file, sheet index, newer col, older col)
CORR = {
    ("HS2007", "HS2002"): ("unsd/HS_2007_to_HS_2002_Correlation_and_conversion_tables.xls", 0, 0, 2),
    ("HS2012", "HS2007"): ("unsd/HS_2012_to_HS_2007_Correlation_and_conversion_tables.xls", 0, 0, 2),
    ("HS2017", "HS2012"): ("unsd/HS2017toHS2012ConversionAndCorrelationTables.xlsx", 1, 0, 2),
    ("HS2022", "HS2017"): ("unsd/HS2022toHS2017ConversionAndCorrelationTables.xlsx", 1, 0, 1),
}

CODE6 = re.compile(r"^\d{6}$")
CAT = re.compile(r"^CER\d{3}$")


def load_creative(version: str) -> pd.DataFrame:
    f = DL / "unctadstat" / f"Dim{version}Products_Creatives_Hierarchy.xls"
    x = pd.read_excel(f, header=None, dtype=str)
    title = str(x.iloc[1, 1]).strip()
    assert version.replace("HS", "HS ") in title, (f, title)
    rows, cat, cat_label, labels = [], None, None, {}
    for code, label in zip(x[2].fillna(""), x[3].fillna("")):
        code, label = code.strip(), label.strip()
        if CAT.match(code):
            cat, cat_label = code, label
            labels[code] = label
        elif CODE6.match(code):
            if cat is None:
                raise ValueError(f"{f}: HS code {code} before any category")
            rows.append((version, cat, cat_label, code, label))
    df = pd.DataFrame(rows, columns=["hs_version", "category_code", "category_label", "hs6", "hs6_label"])
    df.attrs["labels"] = labels
    return df


def load_group_labels() -> dict:
    """Canonical labels from UNCTADstat's group master file (DimCreativeProducts)."""
    x = pd.read_excel(DL / "unctadstat" / "DimCreativeProducts_Creatives_Hierarchy.xls", header=None, dtype=str)
    return {c.strip(): l.strip() for c, l in zip(x[2].fillna(""), x[3].fillna("")) if CAT.match(c.strip())}


def load_corr(newer: str, older: str) -> pd.DataFrame:
    path, sheet, cn, co = CORR[(newer, older)]
    x = pd.read_excel(DL / path, sheet_name=sheet, header=None, dtype=str)
    d = pd.DataFrame({newer: x[cn].str.strip(), older: x[co].str.strip()})
    d = d[d[newer].fillna("").str.match(CODE6) & d[older].fillna("").str.match(CODE6)]
    return d.drop_duplicates().reset_index(drop=True)


def classify(code: str, fwd: dict, bwd: dict) -> tuple[str, list[str]]:
    targets = sorted(fwd.get(code, ()))
    if not targets:
        return "not_in_table", []
    exclusive = all(bwd[t] == {code} for t in targets)
    if len(targets) == 1 and exclusive:
        return ("unchanged_1:1" if targets[0] == code else "renumbered_1:1"), targets
    if len(targets) > 1 and exclusive:
        return "split_1:n", targets
    if len(targets) == 1:
        return "merged_n:1", targets
    return "complex_n:m", targets


def main() -> int:
    lists = {v: load_creative(v) for v in VERSIONS}
    codes = pd.concat(lists.values(), ignore_index=True)

    # sanity: a code should belong to one category within an edition
    dup = codes[codes.duplicated(["hs_version", "hs6"], keep=False)]
    if not dup.empty:
        print("WARNING: codes in >1 category:\n", dup.to_string(), file=sys.stderr)
    codes.to_csv(OUT / "creative_hs_codes.csv", index=False)

    links, summary = [], []
    for a, b in zip(VERSIONS, VERSIONS[1:]):
        corr = load_corr(b, a)
        fwd = corr.groupby(a)[b].apply(set).to_dict()
        bwd = corr.groupby(b)[a].apply(set).to_dict()
        nxt = lists[b].set_index("hs6")["category_code"].to_dict()
        for r in lists[a].itertuples(index=False):
            rel, tg = classify(r.hs6, fwd, bwd)
            in_next = [t for t in tg if t in nxt]
            same_cat = [t for t in in_next if nxt[t] == r.category_code]
            if not tg:
                cov = "n/a"
            elif len(same_cat) == len(tg):
                cov = "all_in_same_category"
            elif len(in_next) == len(tg):
                cov = "all_in_list_other_category"
            elif in_next:
                cov = "partly_in_list"
            else:
                cov = "none_in_list"
            links.append(dict(from_version=a, to_version=b, category_code=r.category_code,
                              category_label=r.category_label, hs6=r.hs6, relationship=rel,
                              n_targets=len(tg), targets=" ".join(tg),
                              code_persists=r.hs6 in tg,
                              targets_in_next_list=cov))
    L = pd.DataFrame(links)
    canon = load_group_labels()
    L["category_label"] = L.category_code.map(canon)
    L.to_csv(OUT / "creative_hs_code_links.csv", index=False)

    # tidy panel table: every category x relationship, zero-filled; plus CER000 total
    rels = ["unchanged_1:1", "renumbered_1:1", "split_1:n", "merged_n:1", "complex_n:m", "not_in_table"]
    # aggregates: CER000 = all creative goods, CER020 = sum of crafts & design subgroups CER021-027
    tot = L.assign(category_code="CER000")
    crafts = L[L.category_code.between("CER021", "CER027")].assign(category_code="CER020")
    allL = pd.concat([L, tot, crafts], ignore_index=True)
    labels = pd.Series({c: canon[c] for c in allL.category_code.unique()})
    g = allL.groupby(["from_version", "to_version", "category_code", "relationship"]).size()
    idx = pd.MultiIndex.from_tuples(
        [(a, b, c, r) for a, b in zip(VERSIONS, VERSIONS[1:]) for c in sorted(labels.index) for r in rels],
        names=g.index.names)
    g = g.reindex(idx, fill_value=0).rename("n_codes").reset_index()
    # drop category rows for edition pairs where the category has no codes
    present = allL.groupby(["from_version", "category_code"]).size()
    g = g[[present.get((a, c), 0) > 0 for a, c in zip(g.from_version, g.category_code)]]
    g.insert(3, "category_label", g.category_code.map(labels))
    g.to_csv(OUT / "creative_hs_continuity.csv", index=False)

    # console summary
    print("codes per edition x category:")
    print(codes.pivot_table(index="category_code", columns="hs_version", values="hs6",
                            aggfunc="count", fill_value=0, margins=True).to_string())
    print("\nrelationship totals (all creative codes):")
    print(pd.crosstab([L.from_version, L.to_version], L.relationship, margins=True).to_string())
    print("\ncode number persists, by relationship:")
    print(pd.crosstab([L.from_version, L.to_version, L.relationship], L.code_persists).to_string())
    print("\nnext-edition list coverage:")
    print(pd.crosstab([L.from_version, L.to_version], L.targets_in_next_list).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
