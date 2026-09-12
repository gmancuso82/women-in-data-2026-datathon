"""Create a small portability-validation dataset from Nigeria NBS Food Price Watch files.

The output retains its own source, currency, geography level, and units. It is
not mixed with the Colombia SIPSA wholesale-market data.
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nigeria_nbs"
PROCESSED = ROOT / "data" / "processed"

SOURCES = {
    "2026-03-01": ("selected_food_table_mar_2026.xlsx", "https://microdata.nigerianstat.gov.ng/index.php/catalog/162/download/1401"),
    "2026-04-01": ("selected_food_table_apr_2026.xlsx", "https://microdata.nigerianstat.gov.ng/index.php/catalog/162/download/1415"),
    "2026-05-01": ("selected_food_table_may_2026.xlsx", "https://microdata.nigerianstat.gov.ng/index.php/catalog/162/download/1427"),
}

FOODS = {
    "Beans Brown": "1 kg",
    "Garri white": "1 kg",
}


def main() -> None:
    records = []
    for date, (filename, source_url) in SOURCES.items():
        sheet = pd.read_excel(RAW / filename, sheet_name="Zone All item")
        subset = sheet.loc[sheet["Item Label"].isin(FOODS)].copy()
        if len(subset) != len(FOODS):
            missing = set(FOODS) - set(subset["Item Label"])
            raise ValueError(f"{filename} is missing expected foods: {sorted(missing)}")
        long = subset.melt(id_vars="Item Label", var_name="zone", value_name="price_ngn")
        long["date"] = date
        long["country"] = "Nigeria"
        long["geography_level"] = "Zone"
        long["item"] = long["Item Label"]
        long["unit"] = long["item"].map(FOODS)
        long["currency"] = "NGN"
        long["source_url"] = source_url
        records.append(long[["date", "country", "geography_level", "zone", "item", "unit", "currency", "price_ngn", "source_url"]])

    output = pd.concat(records, ignore_index=True).sort_values(["date", "item", "zone"])
    PROCESSED.mkdir(parents=True, exist_ok=True)
    output.to_csv(PROCESSED / "nigeria_nbs_zone_prices_march_may_2026.csv", index=False)

    summary = (output.groupby(["date", "item", "unit"], as_index=False)
              .agg(lowest_price_ngn=("price_ngn", "min"), highest_price_ngn=("price_ngn", "max")))
    summary["gap_ngn"] = summary["highest_price_ngn"] - summary["lowest_price_ngn"]
    summary["gap_pct_of_low"] = summary["gap_ngn"] / summary["lowest_price_ngn"] * 100
    for index, row in summary.iterrows():
        subset = output.loc[(output["date"] == row["date"]) & (output["item"] == row["item"])]
        summary.loc[index, "lowest_zone"] = subset.loc[subset["price_ngn"].idxmin(), "zone"]
        summary.loc[index, "highest_zone"] = subset.loc[subset["price_ngn"].idxmax(), "zone"]
    summary.to_csv(PROCESSED / "nigeria_nbs_zone_price_ranges_march_may_2026.csv", index=False)
    print(f"Wrote {len(output)} zone-price observations and {len(summary)} monthly food ranges.")


if __name__ == "__main__":
    main()
