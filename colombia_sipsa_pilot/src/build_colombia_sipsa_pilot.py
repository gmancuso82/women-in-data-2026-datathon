"""Build a tidy Colombia SIPSA pilot table from official daily Excel workbooks.

The SIPSA daily workbook is published in a wide format: each market has a
price column and a day-to-day change column. This script retains only the two
selected markets and writes one observation per food, market, and date.

This is a wholesale fresh-food price monitor. It is not an official retail
Cost of a Healthy Diet (CoHD) calculation.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "colombia_sipsa_pilot.csv"

MONTHS = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

MARKETS = {
    "Bogotá": {"match": "Bogotá", "market": "Corabastos"},
    "Medellín": {"match": "Medellín", "market": "Central Mayorista de Antioquia (CMA)"},
}


def source_date(path: Path) -> str:
    """Read a date such as 12feb2025 from a SIPSA workbook filename."""
    match = re.search(r"(\d{2})([a-z]{3})(\d{4})", path.stem.lower())
    if not match:
        raise ValueError(f"Could not find a SIPSA date in {path.name}")
    day, month_name, year = match.groups()
    return f"{year}-{MONTHS[month_name]:02d}-{day}"


def food_group(label: str) -> str | None:
    """Recognize the source's three fresh-food section labels."""
    clean = label.lower()
    if "hortal" in clean or "verdura" in clean:
        return "Vegetables"
    if "fruta" in clean:
        return "Fruit"
    # Do not match individual items such as "Plátano guineo" here.
    if clean.startswith("tubérculo") or clean.startswith("tuberculo"):
        return "Tubers and plantains"
    return None


def source_url(date: str) -> str:
    """Recreate the official DANE URL for provenance in the output table."""
    timestamp = pd.Timestamp(date)
    month_abbr = list(MONTHS)[timestamp.month - 1]
    filename = f"anex-SIPSADiario-{timestamp.day:02d}{month_abbr}{timestamp.year}.xlsx"
    return f"https://www.dane.gov.co/files/operaciones/SIPSA/{filename}"


def clean_workbook(path: Path) -> pd.DataFrame:
    """Convert one official SIPSA daily workbook from wide to tidy format."""
    raw = pd.read_excel(path, header=None)
    market_headers = raw.iloc[2]
    observation_date = source_date(path)
    rows: list[dict[str, object]] = []
    current_group: str | None = None

    for _, row in raw.iloc[4:].iterrows():
        label = row.iloc[0]
        if pd.isna(label):
            continue

        label = str(label).strip()
        section = food_group(label)
        if section is not None:
            current_group = section
            continue

        if current_group is None or label.startswith(("*", "n.d.", "Var%")):
            continue

        for city, details in MARKETS.items():
            columns = market_headers[
                market_headers.astype(str).str.contains(details["match"], case=False, na=False)
            ].index
            if len(columns) != 1:
                raise ValueError(f"Expected one price column for {city}; found {len(columns)}")

            price_column = columns[0]
            price = pd.to_numeric(row.iloc[price_column], errors="coerce")
            change_pct = pd.to_numeric(row.iloc[price_column + 1], errors="coerce")
            if pd.isna(price):
                continue

            rows.append(
                {
                    "date": observation_date,
                    "city": city,
                    "market": details["market"],
                    "item": label.replace("*", "").strip(),
                    "item_source_label": label,
                    "food_group": current_group,
                    "unit": "COP per kg",
                    "price_average_cop_per_kg": float(price),
                    "price_change_pct_from_previous_market_day": change_pct,
                    "source_url": source_url(observation_date),
                    "extraction_method": "official_xlsx",
                    "review_flag": False,
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    files = sorted(INPUT_DIR.glob("sipsa-*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No SIPSA workbooks found in {INPUT_DIR}")

    tidy = pd.concat([clean_workbook(path) for path in files], ignore_index=True)
    tidy = tidy.sort_values(["date", "city", "food_group", "item"]).reset_index(drop=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    tidy.to_csv(OUTPUT_FILE, index=False)

    print(f"Wrote {len(tidy):,} observations to {OUTPUT_FILE}")
    print("\nObservations by date and city:")
    print(tidy.groupby(["date", "city"]).size().unstack(fill_value=0))
    print("\nFood groups:")
    print(tidy["food_group"].value_counts())


if __name__ == "__main__":
    main()
