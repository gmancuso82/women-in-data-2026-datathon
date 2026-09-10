"""Compare Bogotá, Medellín, and Montería using foods present everywhere.

The two-market pilot retains its original 10-food reference basket. This
script deliberately creates a separate, directly comparable basket for three
markets: only selected foods observed in every city on every sampled date are
included. It is a wholesale fresh-food price comparison, not retail CoHD.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = PROJECT_ROOT / "data" / "processed" / "colombia_sipsa_pilot.csv"
BASKET_FILE = PROJECT_ROOT / "data" / "basket_definition.csv"
TOTALS_FILE = PROJECT_ROOT / "data" / "processed" / "three_market_shared_basket_totals.csv"
SPREADS_FILE = PROJECT_ROOT / "data" / "processed" / "three_market_item_spreads.csv"
AVAILABILITY_FILE = PROJECT_ROOT / "data" / "processed" / "three_market_basket_availability.csv"

CITIES = ["Bogotá", "Medellín", "Montería"]


def main() -> None:
    prices = pd.read_csv(PRICE_FILE)
    basket = pd.read_csv(BASKET_FILE)
    # Food group comes from the SIPSA source table; retain basket metadata
    # without creating duplicate food_group columns during the merge.
    basket_metadata = basket[
        ["item", "basket_role", "kilograms_in_reference_basket"]
    ]
    selected = prices.merge(
        basket_metadata, on="item", how="inner", validate="many_to_one"
    )
    selected = selected.loc[selected["city"].isin(CITIES)].copy()

    expected_city_dates = len(CITIES) * selected["date"].nunique()
    availability = (
        selected.assign(present=True)
        .pivot_table(
            index=["item", "food_group", "basket_role"],
            columns=["date", "city"],
            values="present",
            aggfunc="any",
            fill_value=False,
        )
        .reset_index()
    )
    presence_columns = availability.columns[3:]
    availability["city_date_observations"] = availability[presence_columns].sum(axis=1)
    availability["included_in_three_market_shared_basket"] = (
        availability["city_date_observations"] == expected_city_dates
    )
    availability.to_csv(AVAILABILITY_FILE, index=False)

    common_items = availability.loc[
        availability["included_in_three_market_shared_basket"], "item"
    ].tolist()
    shared = selected.loc[selected["item"].isin(common_items)].copy()
    shared["cost_cop"] = (
        shared["price_average_cop_per_kg"] * shared["kilograms_in_reference_basket"]
    )

    totals = (
        shared.groupby(["date", "city", "market"], as_index=False)
        .agg(
            foods_in_shared_basket=("item", "nunique"),
            equal_weight_shared_basket_cop=("cost_cop", "sum"),
        )
        .sort_values(["date", "equal_weight_shared_basket_cop"])
    )
    totals.to_csv(TOTALS_FILE, index=False)

    item_prices = shared.pivot(
        index=["date", "item", "food_group", "basket_role"],
        columns="city",
        values="price_average_cop_per_kg",
    ).reset_index()
    item_prices["highest_price_cop_per_kg"] = item_prices[CITIES].max(axis=1)
    item_prices["lowest_price_cop_per_kg"] = item_prices[CITIES].min(axis=1)
    item_prices["market_spread_cop_per_kg"] = (
        item_prices["highest_price_cop_per_kg"] - item_prices["lowest_price_cop_per_kg"]
    )
    item_prices["highest_price_city"] = item_prices[CITIES].idxmax(axis=1)
    item_prices["lowest_price_city"] = item_prices[CITIES].idxmin(axis=1)
    item_prices = item_prices.sort_values(["date", "market_spread_cop_per_kg"], ascending=[True, False])
    item_prices.to_csv(SPREADS_FILE, index=False)

    excluded = sorted(set(basket["item"]) - set(common_items))
    print("Three-market shared basket foods:")
    print(", ".join(common_items))
    print("\nExcluded because they are not present for every market/date:")
    print(", ".join(excluded) if excluded else "None")
    print("\nShared-basket totals (COP):")
    print(totals.to_string(index=False))
    print("\nLargest item-level market spreads (COP/kg):")
    print(item_prices.groupby("date").head(3).to_string(index=False))


if __name__ == "__main__":
    main()
