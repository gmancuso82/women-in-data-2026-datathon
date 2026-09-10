"""Identify which selected foods contribute to the Bogotá-Medellín price gap."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = PROJECT_ROOT / "data" / "processed" / "colombia_sipsa_pilot.csv"
BASKET_FILE = PROJECT_ROOT / "data" / "basket_definition.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "food_price_gap_by_item.csv"


def main() -> None:
    prices = pd.read_csv(PRICE_FILE)
    basket = pd.read_csv(BASKET_FILE)
    selected = prices.merge(basket[["item"]], on="item", how="inner")

    gaps = (
        selected.pivot(
            index=["date", "item", "food_group"],
            columns="city",
            values="price_average_cop_per_kg",
        )
        .reset_index()
        .rename(columns={"Bogotá": "bogota_cop_per_kg", "Medellín": "medellin_cop_per_kg"})
    )
    gaps["bogota_minus_medellin_cop_per_kg"] = (
        gaps["bogota_cop_per_kg"] - gaps["medellin_cop_per_kg"]
    )
    gaps["higher_price_market"] = gaps["bogota_minus_medellin_cop_per_kg"].map(
        lambda value: "Bogotá" if value > 0 else "Medellín" if value < 0 else "Same price"
    )
    gaps = gaps.sort_values(["date", "bogota_minus_medellin_cop_per_kg"], ascending=[True, False])
    gaps.to_csv(OUTPUT_FILE, index=False)
    print(gaps.to_string(index=False))


if __name__ == "__main__":
    main()
