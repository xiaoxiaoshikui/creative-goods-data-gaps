"""Build the dashboard data file from public UNCTADstat and UN M49 sources.

Inputs (downloaded by scripts/download.sh into data/raw/):
  - US_CreativeGoodsValue.csv  UNCTADstat bulk download, "Creative goods: value"
  - m49.csv                    UN Statistics Division, Standard country or area codes (M49)

Output:
  - docs/data/dashboard.json   everything the web page needs

Run: python scripts/build_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "docs" / "data" / "dashboard.json"

CATS = {
    "CER000": "All creative goods",
    "CER010": "Audiovisual, multimedia & photography",
    "CER020": "Crafts & design goods",
    "CER030": "Books & publishing",
    "CER040": "Music, performing & visual arts",
    "CER050": "Architecture",
    "CER060": "Software, video games & recorded media",
    "CER070": "Cultural & natural heritage",
}
DESIGN_SUB = {
    "CER021": "Carpets", "CER022": "Fashion accessories", "CER023": "Interior",
    "CER024": "Jewellery", "CER025": "Toys", "CER026": "Wickerware", "CER027": "Yarn",
}
GROUPS = {
    "0000": "World", "1500": "Developed economies", "1400": "Developing economies",
    "1600": "Developing economies excl. China", "1610": "Least developed countries",
    "1640": "Small island developing States", "1620": "Landlocked developing countries",
}
# Economies UNCTADstat reports that are not in the M49 overview table
EXTRA_ISO3 = {"158": "TWN", "530": "ANT", "890": "YUG", "891": "SCG", "736": "SDN", "200": "CSK"}

# Code changes: splice the old code into the current one for the years it was used
SPLICE = [("736", "729", 2002, 2011),   # Sudan (...2011) -> Sudan
          ("960", "360", 2002, 2002)]   # Indonesia (...2002) -> Indonesia
# Sovereign states with no reporter rows at all in UNCTADstat (they appear only as partners).
# Counted as missing in every year; South Sudan from independence (2011).
ABSENT_STATES = {"706": 2002, "728": 2011, "148": 2002, "332": 2002, "226": 2002,
                 "795": 2002, "408": 2002, "584": 2002, "520": 2002}
BOOT_SEED, BOOT_B = 20261118, 20000

FULL_YEARS = list(range(2002, 2024))  # 2024 kept separately: reporting lag
LAST_YEAR = 2024


def load() -> pd.DataFrame:
    con = duckdb.connect()
    src = str(RAW / "US_CreativeGoodsValue.csv")
    df = con.execute(
        f"""
        SELECT Year AS year, Economy AS code, "Economy Label" AS name, Flow AS flow,
               Product AS product, "US$ at current prices in millions" AS usd,
               "US$ at current prices in millions Footnote" AS note,
               "US$ at current prices in millions Missing value" AS mv,
               "Percentage of total world" AS pct_world,
               "Percentage of total merchandise trade" AS pct_merch
        FROM read_csv_auto('{src}', types={{'Economy':'VARCHAR','Partner':'VARCHAR','Flow':'VARCHAR'}})
        WHERE Partner = '0000'
        """
    ).df()
    return df


def m49() -> pd.DataFrame:
    t = pd.read_csv(RAW / "m49.csv", dtype={"M49 Code": str})
    t["code"] = t["M49 Code"].str.zfill(3)
    t = t.rename(columns={
        "ISO-alpha3 Code": "iso3", "Region Name": "region", "Sub-region Name": "subregion",
        "Least Developed Countries (LDC)": "ldc", "Land Locked Developing Countries (LLDC)": "lldc",
        "Small Island Developing States (SIDS)": "sids",
    })
    for c in ("ldc", "lldc", "sids"):
        t[c] = t[c].notna()
    t = t.rename(columns={"Country or Area": "country", "ISO-alpha2 Code": "iso2"})
    return t[["code", "iso3", "iso2", "country", "region", "subregion", "ldc", "lldc", "sids"]]


def clean(o):
    """Replace NaN with None and numpy scalars with Python types so the output is valid JSON."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()
    if isinstance(o, float) and o != o:
        return None
    return o


def sig(x, n=3):
    """Round to n significant figures, so small exporters are not rounded to zero."""
    if pd.isna(x):
        return None
    x = float(x)
    if x == 0:
        return 0.0
    from math import floor, log10
    return round(x, -int(floor(log10(abs(x)))) + (n - 1))


def r(x, nd=1):
    return None if pd.isna(x) else round(float(x), nd)


def main() -> None:
    df = load()
    ex = df[df.flow == "02"]
    meta = m49()

    # ---- 1. Trend by group (US$ bn, exports) -------------------------------------
    g = ex[(ex["product"] == "CER000") & ex.code.isin(GROUPS)]
    trend = {GROUPS[c]: [r(v / 1000, 2) for v in s.sort_values("year").usd]
             for c, s in g.groupby("code")}
    years_all = sorted(ex.year.unique().tolist())
    china = ex[(ex["product"] == "CER000") & (ex.code == "156")].sort_values("year")
    trend["China"] = [r(v / 1000, 2) for v in china.usd]
    world = g[g.code == "0000"].sort_values("year")
    trend_pct_merch = [r(v, 2) for v in world.pct_merch]
    estimated_groups = sorted({GROUPS[c] for c in g[g.note == "Estimated"].code})

    # ---- 2. Category composition, latest year ------------------------------------
    def comp(code, year):
        s = ex[(ex.code == code) & (ex.year == year)].set_index("product").usd
        return {k: r(s.get(k, float("nan")) / 1000, 2) for k in list(CATS) + list(DESIGN_SUB)}

    composition = {GROUPS[c]: comp(c, 2023) for c in ("0000", "1500", "1400", "1600", "1610", "1640")}

    # ---- 3. Economy-level panel (exports, top-level categories) ------------------
    econ = ex[ex.code.str.len() == 3].merge(meta, on="code", how="left")
    econ["iso3"] = econ["iso3"].fillna(econ.code.map(EXTRA_ISO3))
    econ_meta = (econ.drop_duplicates("code")
                 .set_index("code")[["name", "iso3", "region", "subregion", "ldc", "lldc", "sids"]])

    panel = {}
    for code, s in econ[econ["product"].isin(CATS)].groupby("code"):
        piv = s.pivot_table(index="year", columns="product", values="usd", aggfunc="first")
        piv = piv.reindex(years_all)
        tot = s[s["product"] == "CER000"].set_index("year").reindex(years_all)
        panel[code] = {
            "v": {p: [sig(x) for x in piv[p]] if p in piv else [None] * len(years_all) for p in CATS},
            "pm": [r(x, 2) for x in tot.pct_merch],
            "pw": [r(x, 3) for x in tot.pct_world],
        }

    # ---- 4. Coverage / data gaps --------------------------------------------------
    # Status of each current economy-year for total creative goods exports:
    #   value          a value is published
    #   not_applicable UNCTADstat marks the economy as not applicable (e.g. not yet in existence): excluded
    #   unpublished    the row exists but no value is published ("Not publishable" etc.)
    #   no_row         the economy has no row for that year
    #   absent         the economy never appears as a reporter (ABSENT_STATES)
    tot_all = ex[(ex["product"] == "CER000") & (ex.code.str.len() == 3)].copy()
    for old, new_code, y0, y1 in SPLICE:
        tot_all = tot_all[~((tot_all.code == new_code) & tot_all.year.between(y0, y1))]
        tot_all.loc[(tot_all.code == old) & tot_all.year.between(y0, y1), "code"] = new_code
    current = set(meta.code) | {"158"}
    tot_all = tot_all[tot_all.code.isin(current)]
    years_cov = FULL_YEARS + [LAST_YEAR]
    status = {}
    for row in tot_all.itertuples():
        if pd.notna(row.usd):
            status[(row.code, row.year)] = "value"
        elif isinstance(row.mv, str) and row.mv.strip().lower() == "not applicable":
            status[(row.code, row.year)] = "not_applicable"
        else:
            status[(row.code, row.year)] = "unpublished"
    reporters = sorted(set(tot_all.code))
    meta_i = meta.set_index("code")
    names = econ.drop_duplicates("code").set_index("code")["name"].to_dict()
    names.update({"729": "Sudan", "360": "Indonesia"})

    def info(code):
        m = meta_i.loc[code] if code in meta_i.index else None
        iso3 = (m["iso3"] if m is not None else None) or EXTRA_ISO3.get(code)
        return {
            "code": code, "iso3": iso3,
            "name": names.get(code) or (m["country"] if m is not None and "country" in m else code),
            "region": m["region"] if m is not None and isinstance(m["region"], str) else None,
            "ldc": bool(m["ldc"]) if m is not None else False,
            "lldc": bool(m["lldc"]) if m is not None else False,
            "sids": bool(m["sids"]) if m is not None else False,
        }

    rows, yearly = [], []
    for code in reporters + sorted(ABSENT_STATES):
        absent = code in ABSENT_STATES
        st = {y: ("absent" if absent and y >= ABSENT_STATES[code] else
                  "not_applicable" if absent else status.get((code, y), "no_row")) for y in years_cov}
        yrs = [y for y in FULL_YEARS if st[y] != "not_applicable"]
        if not yrs:
            continue
        rep = [y for y in yrs if st[y] == "value"]
        d = info(code)
        d["name"] = {"728": "South Sudan", "520": "Nauru", "408": "DPR Korea"}.get(code, d["name"])
        d.update({
            "absent": absent, "years_listed": len(yrs), "years_reported": len(rep),
            "gap_years": len(yrs) - len(rep),
            "reported_latest": st[LAST_YEAR] == "value",
            "last_year": max([y for y in years_cov if st[y] == "value"], default=None),
        })
        rows.append(d)
        for y in years_cov:
            if st[y] != "not_applicable":
                yearly.append((code, y, st[y] == "value", d["ldc"], d["sids"], d["lldc"]))
    cov = pd.DataFrame(rows)
    cov["gap_share"] = cov.gap_years / cov.years_listed

    def summarize(mask, label):
        c = cov[mask]
        return {
            "group": label, "n": int(len(c)), "n_absent": int(c.absent.sum()),
            "mean_gap_pct": r(c.gap_share.mean() * 100, 1),
            "median_gap_pct": r(c.gap_share.median() * 100, 1),
            "pooled_gap_pct": r(c.gap_years.sum() / c.years_listed.sum() * 100, 1),
            "share_any_gap_pct": r((c.gap_share > 0).mean() * 100, 1),
            "share_missing_latest_pct": r((~c.reported_latest).mean() * 100, 1),
        }

    other = ~(cov.ldc | cov.sids | cov.lldc)
    cov_groups = [
        summarize(cov.ldc, "Least developed countries"),
        summarize(cov.sids, "Small island developing States"),
        summarize(cov.lldc, "Landlocked developing countries"),
        summarize(other, "All other economies"),
        summarize(cov.code.notna(), "All economies"),
    ]
    cov_regions = [summarize(cov.region == reg, reg) for reg in sorted(cov.region.dropna().unique())]

    # Uncertainty for the LDC vs other comparison: bootstrap over economies, permutation test
    rng = np.random.default_rng(BOOT_SEED)
    a, b = cov[cov.ldc].gap_share.to_numpy(), cov[other].gap_share.to_numpy()
    ra = rng.choice(a, (BOOT_B, len(a))).mean(1)
    rb = rng.choice(b, (BOOT_B, len(b))).mean(1)
    pool, obs = np.concatenate([a, b]), a.mean() - b.mean()
    perm = np.array([(lambda q: q[:len(a)].mean() - q[len(a):].mean())(rng.permutation(pool)) for _ in range(BOOT_B)])
    ldc_test = {
        "n_ldc": int(len(a)), "n_other": int(len(b)),
        "diff_pp": r(obs * 100, 1), "diff_ci95": [r(x * 100, 1) for x in np.percentile(ra - rb, [2.5, 97.5])],
        "ratio": r(a.mean() / b.mean(), 1), "ratio_ci95": [r(x, 1) for x in np.percentile(ra / rb, [2.5, 97.5])],
        "perm_p_one_sided": float((np.sum(perm >= obs) + 1) / (BOOT_B + 1)),
        "share_zero_gap_pct": [r((a == 0).mean() * 100, 0), r((b == 0).mean() * 100, 0)],
        "method": f"Bootstrap over economies ({BOOT_B} draws) and one-sided permutation test, seed {BOOT_SEED}",
    }

    Yd = pd.DataFrame(yearly, columns=["code", "year", "has", "ldc", "sids", "lldc"])
    missing_by_year = []
    for y in years_cov:
        s_ = Yd[Yd.year == y]
        missing_by_year.append({"year": int(y), "listed": int(len(s_)), "missing": int((~s_.has).sum()),
                                "missing_ldc": int((~s_.has & s_.ldc).sum()), "n_ldc": int(s_.ldc.sum())})

    # ---- 5. HS revisions: stability of the creative-goods definition --------------
    hs_rows = []
    links = pd.read_csv(ROOT / "data" / "hs" / "creative_hs_code_links.csv", dtype={"hs6": str})
    for (fv, tv), s in links.groupby(["from_version", "to_version"], sort=True):
        rel = s.relationship.value_counts()
        hs_rows.append({
            "pair": f"{fv[2:]}→{tv[2:]}", "total": int(len(s)),
            "kept": int(rel.get("unchanged_1:1", 0)),
            "renumbered": int(rel.get("renumbered_1:1", 0)),
            "split": int(rel.get("split_1:n", 0)),
            "merged": int(rel.get("merged_n:1", 0)),
            "complex": int(rel.get("complex_n:m", 0)),
            "complex_persists": int(((s.relationship == "complex_n:m") & (s.code_persists.astype(str) == "True")).sum()),
        })
    last_pair = links[(links.from_version == "HS2017") & (links.to_version == "HS2022")]
    hs_cat = []
    for (cc, cl), s in last_pair.groupby(["category_code", "category_label"]):
        if cc in ("CER000", "CER020"):
            continue
        carve = (s.relationship == "complex_n:m") & (s.code_persists.astype(str) == "True")
        real = ~s.relationship.isin(["unchanged_1:1", "renumbered_1:1"]) & ~carve
        hs_cat.append({"code": cc, "label": cl, "codes": int(len(s)), "changed": int(real.sum()),
                       "carveout": int(carve.sum())})
    codes = pd.read_csv(ROOT / "data" / "hs" / "creative_hs_codes.csv", dtype=str)
    vcol = [c for c in codes.columns if "version" in c or "edition" in c][0]
    hs_counts = codes.groupby(vcol).size().to_dict()

    # Map helpers: centroid points for small island States and economies missing from the base map
    topo = json.loads((ROOT / "docs" / "assets" / "world_50m.json").read_text())
    drawn = {g.get("id") for g in topo["objects"]["countries"]["geometries"]}
    cen = pd.read_csv(RAW / "geo" / "centroids.csv", keep_default_na=False).set_index("country")
    iso2 = meta.set_index("iso3")["iso2"].to_dict()
    points = {}
    for row in cov.itertuples():
        if row.iso3 and (row.sids or row.iso3 not in drawn):
            k = iso2.get(row.iso3)
            if k in cen.index:
                points[row.iso3] = [float(cen.loc[k, "latitude"]), float(cen.loc[k, "longitude"])]

    out = {
        "meta": {
            "source": "UNCTADstat, Creative goods: value (US_CreativeGoodsValue), bulk download",
            "source_url": "https://unctadstat.unctad.org/datacentre/dataviewer/US.CreativeGoodsValue",
            "m49_url": "https://unstats.un.org/unsd/methodology/m49/overview/",
            "accessed": "2026-11-18",
            "unit": "US$ at current prices",
            "flow": "Exports to the world",
            "years": [int(y) for y in years_all],
            "categories": CATS, "design_sub": DESIGN_SUB,
            "estimated_groups": estimated_groups,
        },
        "trend": trend, "trend_pct_merch": trend_pct_merch,
        "composition_2023": composition,
        "economies": {c: {k: (v if not (isinstance(v, float) and pd.isna(v)) else None)
                          for k, v in econ_meta.loc[c].to_dict().items()} for c in panel},
        "panel": panel,
        "coverage": cov.drop(columns=["gap_share"]).assign(gap_pct=(cov.gap_share * 100).round(1)).to_dict("records"),
        "points": points, "coverage_groups": cov_groups, "coverage_regions": cov_regions, "ldc_test": ldc_test,
        "missing_by_year": missing_by_year,
        "hs_pairs": hs_rows, "hs_categories_2022": hs_cat,
        "hs_list_size": {str(k): int(v) for k, v in hs_counts.items()},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cov.drop(columns=["gap_share"]).assign(gap_pct=(cov.gap_share * 100).round(1)).sort_values("gap_pct", ascending=False) \
        .to_csv(OUT.parent / "coverage.csv", index=False)
    OUT.write_text(json.dumps(clean(out), separators=(",", ":"), allow_nan=False))
    print(f"wrote {OUT} ({OUT.stat().st_size/1e3:.0f} kB)")
    print(json.dumps(cov_groups, indent=1))
    print(json.dumps(cov_regions, indent=1))


if __name__ == "__main__":
    main()
