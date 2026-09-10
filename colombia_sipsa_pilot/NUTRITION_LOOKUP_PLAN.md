# Nutrition lookup for the Local Healthy Food Swap Monitor

## What this layer does

The food-market price monitor identifies local price gaps. This lookup makes the next question possible: **when a food becomes relatively expensive, is there a lower-cost food in the same nutrition role?**

The monitor will offer a possible swap only when both foods have a verified nutrient profile and the same defined role. It will not claim that every fruit, vegetable, or starch is interchangeable.

## Official nutrient source

The intended source is the Colombian Food Composition Table (TCAC), maintained by the Instituto Colombiano de Bienestar Familiar (ICBF):

https://www.icbf.gov.co/tabla-de-composicion-de-alimentos-colombianos-tcac

The TCAC covers foods consumed in Colombia and is intended to support diet planning and nutrition research. Each value must be traced to a specific TCAC food entry and preparation state.

## What has been entered so far

`data/nutrition_lookup.csv` contains the ten foods in our price basket, their proposed nutrition roles, and the exact TCAC search term to verify. Numeric nutrient fields are intentionally blank until we confirm the match.

This is important because a market label is not always a one-to-one nutrition-database entry. For example, the correct entry may depend on the variety, edible portion, and whether the food is raw or cooked.

### First verified vegetable profiles

- **Zanahoria:** matched to TCAC 2018 entry `B110 — Zanahoria, sin cáscara, cruda`. Complete pilot nutrient fields are entered per 100 g edible portion.
- **Ahuyama:** matched to TCAC 2018 entry `B006 — Ahuyama, cruda`. Complete pilot nutrient fields are entered per 100 g edible pulp without seeds.
- **Vitamin A:** TCAC reports Vitamin A in equivalent retinol (ER), so the monitor retains that unit rather than converting it to RAE.

### First starch matching decisions

- **Yuca:** matched to TCAC 2018 entry `B107 — Yuca blanca, sin cáscara, cruda`. Complete pilot nutrient fields are entered per 100 g edible portion.
- **Chócolo mazorca:** not yet matched. A food-composition entry must state whether it refers to tender kernels or the whole cob. The SIPSA price can reflect the market product, including the cob, so a per-kilogram price cannot yet be compared directly with nutrition per 100 grams of edible kernels.

## Unit-compatibility gate

Before displaying a **cost per nutrient** figure or ranking one food as the cheaper nutrient option, the monitor checks that the price and nutrition quantities refer to the same edible amount.

| Question | Example | Monitor action |
| --- | --- | --- |
| Is the market product already edible? | Peeled, edible food | A cost-per-nutrient calculation may proceed once the nutrition record is verified. |
| Does the market product include waste? | Whole corn cob versus kernels | Require an edible-yield factor or show price comparison only. |
| Is preparation state different? | Raw market yuca versus cooked table entry | Do not mix the records without a documented conversion. |

## Fields we will add after verification

All values will be standardized per 100 grams of edible food:

- energy (kcal)
- protein (g)
- fiber (g)
- fat (g)
- iron (mg)
- calcium (mg)
- vitamin A (micrograms RAE)
- vitamin C (mg)

## First decision rules for swaps

| Nutrition role | Current foods | Early monitor behavior |
| --- | --- | --- |
| Root or fresh-corn starch | Yuca, Chócolo mazorca | Compare price and the verified energy/fiber profile only after the unit-compatibility gate is met; then flag a lower-cost option when it meets the role rule. |
| Orange vegetable | Zanahoria, Ahuyama | Compare price and the verified vitamin-A/fiber profile; do not use a lower-cost food that fails the role rule. |
| Fruit variety | Banano, Naranja, Guayaba | Compare price and verified fruit nutrient profile; state clearly what nutrient trade-off a swap creates. |
| Dietary-fat food | Aguacate | Report price pressure and nutrition profile. Do not recommend a direct substitute unless an approved comparable food is in the basket. |
| Cooking base | Cebolla cabezona blanca, Tomate | Track access and price, but do not automatically classify as a nutrient-equivalent swap pair. |

## Guardrails for our presentation

- SIPSA prices are wholesale food-market observations, not household retail prices and not a local CoHD estimate.
- A proposed swap is a decision-support prompt, not a nutrition prescription or proof that households will buy the alternative.
- We will report associations and observed price differences, not causes.
- The current basket contains no verified protein source. The monitor should show that gap rather than pretending the basket is nutritionally complete.
