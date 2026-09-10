"""Create transparent, nutrition-aware price actions for carrot and ahuyama.

This pilot compares market prices within one defined nutrition role. It does not
estimate retail cost of a healthy diet or calculate cost per nutrient.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = PROJECT_ROOT / "data" / "processed" / "food_price_gap_by_item.csv"
NUTRITION_FILE = PROJECT_ROOT / "data" / "nutrition_lookup.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "orange_vegetable_actions.csv"

ROLE = "Orange vegetable role"
# Pilot role guardrails. These are not dietary requirements or health advice.
MIN_VITAMIN_A_ER = 1_000
MIN_FIBER_G = 0.8
NUTRIENT_COLUMNS = [
    "energy_kcal_per_100g",
    "protein_g_per_100g",
    "fiber_g_per_100g",
    "fat_g_per_100g",
    "iron_mg_per_100g",
    "calcium_mg_per_100g",
    "vitamin_a_er_per_100g",
    "vitamin_c_mg_per_100g",
]


def describe_tradeoffs(expensive: pd.Series, lower_cost: pd.Series) -> str:
    """Describe the nutrition differences without declaring the foods equivalent."""
    comparisons = [
        ("energy", "energy_kcal_per_100g", "kcal"),
        ("fiber", "fiber_g_per_100g", "g fiber"),
        ("iron", "iron_mg_per_100g", "mg iron"),
        ("calcium", "calcium_mg_per_100g", "mg calcium"),
        ("vitamin A", "vitamin_a_er_per_100g", "ER vitamin A"),
        ("vitamin C", "vitamin_c_mg_per_100g", "mg vitamin C"),
    ]
    higher = []
    lower = []

    for label, column, unit in comparisons:
        difference = lower_cost[column] - expensive[column]
        if difference > 0:
            higher.append(f"higher {label} ({difference:g} {unit})")
        elif difference < 0:
            lower.append(f"lower {label} ({abs(difference):g} {unit})")

    parts = []
    if higher:
        parts.append("; ".join(higher))
    if lower:
        parts.append("; ".join(lower))
    return "; ".join(parts) if parts else "No difference in selected pilot nutrients"


def main() -> None:
    price_gaps = pd.read_csv(PRICE_FILE)
    nutrition = pd.read_csv(NUTRITION_FILE)
    role_foods = nutrition.loc[
        (nutrition["proposed_nutrition_role"] == ROLE)
        & (nutrition["tcac_match_status"] == "verified_tcac_match"),
        ["item", *NUTRIENT_COLUMNS],
    ].copy()

    if len(role_foods) < 2:
        raise ValueError("At least two verified foods are required for an orange-vegetable action.")

    for column in NUTRIENT_COLUMNS:
        role_foods[column] = pd.to_numeric(role_foods[column], errors="raise")

    market_prices = price_gaps.melt(
        id_vars=["date", "item"],
        value_vars=["bogota_cop_per_kg", "medellin_cop_per_kg"],
        var_name="market",
        value_name="market_price_cop_per_kg",
    )
    market_prices["market"] = market_prices["market"].map(
        {"bogota_cop_per_kg": "Bogotá", "medellin_cop_per_kg": "Medellín"}
    )
    role_prices = market_prices.merge(role_foods, on="item", how="inner")

    actions = []
    for (date, market), group in role_prices.groupby(["date", "market"], sort=True):
        group = group.sort_values("market_price_cop_per_kg").reset_index(drop=True)
        lower_cost = group.iloc[0]
        expensive = group.iloc[-1]
        meets_guardrails = (
            lower_cost["vitamin_a_er_per_100g"] >= MIN_VITAMIN_A_ER
            and lower_cost["fiber_g_per_100g"] >= MIN_FIBER_G
        )
        status = "Potential lower-cost alternative" if meets_guardrails else "Review needed"

        actions.append(
            {
                "date": date,
                "market": market,
                "higher_price_orange_vegetable": expensive["item"],
                "higher_price_cop_per_kg": expensive["market_price_cop_per_kg"],
                "lower_cost_alternative": lower_cost["item"],
                "lower_cost_cop_per_kg": lower_cost["market_price_cop_per_kg"],
                "potential_savings_cop_per_kg": (
                    expensive["market_price_cop_per_kg"] - lower_cost["market_price_cop_per_kg"]
                ),
                "action_status": status,
                "nutrition_tradeoff_per_100g": describe_tradeoffs(expensive, lower_cost),
                "role_guardrail": (
                    f"Vitamin A >= {MIN_VITAMIN_A_ER:g} ER and fibre >= {MIN_FIBER_G:g} g per 100 g"
                ),
                "unit_note": "Price comparison only. No cost-per-nutrient calculation until edible-yield units align.",
            }
        )

    action_table = pd.DataFrame(actions)
    action_table.to_csv(OUTPUT_FILE, index=False)
    print(action_table.to_string(index=False))


if __name__ == "__main__":
    main()
