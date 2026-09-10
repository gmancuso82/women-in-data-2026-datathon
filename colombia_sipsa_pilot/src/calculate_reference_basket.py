"""Calculate the selected equal-weight fresh-food reference basket.

Each selected food contributes one kilogram because SIPSA publishes the
average wholesale price in COP per kilogram. This makes a transparent first
comparison of markets and seasons; it is not a consumer basket or an official
retail Cost of a Healthy Diet (CoHD) calculation.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = PROJECT_ROOT / "data" / "processed" / "colombia_sipsa_pilot.csv"
BASKET_FILE = PROJECT_ROOT / "data" / "basket_definition.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "reference_basket_totals.csv"


def main() -> None:
    prices = pd.read_csv(PRICE_FILE)
    basket = pd.read_csv(BASKET_FILE)

    selected = prices.merge(basket, on="item", how="inner", validate="many_to_one")
    expected_items = basket["item"].nunique()
    observed_items = selected.groupby(["date", "city"])["item"].nunique()
    if not observed_items.eq(expected_items).all():
        raise ValueError("At least one market/date is missing a selected basket item.")

    selected["cost_cop"] = (
        selected["price_average_cop_per_kg"]
        * selected["kilograms_in_reference_basket"]
    )
    totals = (
        selected.groupby(["date", "city", "market"], as_index=False)
        .agg(
            foods_in_basket=("item", "nunique"),
            equal_weight_reference_basket_cop=("cost_cop", "sum"),
        )
        .sort_values(["date", "city"])
    )
    totals.to_csv(OUTPUT_FILE, index=False)
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main()
