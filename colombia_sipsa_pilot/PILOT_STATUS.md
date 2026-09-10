# Colombia SIPSA pilot - where we are

## Our question

Can standardized local food-market price observations reveal location and seasonal differences that a national annual healthy-diet estimate can hide?

**Important:** SIPSA supplies wholesale market prices. Our output is a *fresh-food market-price proxy*, not an official retail Cost of a Healthy Diet (CoHD).

## Pilot choices

| Part | Decision |
|---|---|
| Country | Colombia |
| Market 1 | Bogota - Corabastos |
| Market 2 | Medellin - Central Mayorista de Antioquia (CMA) |
| Source | Official DANE/SIPSA daily price workbooks |
| Unit | Colombian pesos per kilogram (COP/kg) |
| Dates | 12 Feb, 14 May, 13 Aug, and 12 Nov 2025 |

## What the cleaned data contains

| Check | Result |
|---|---:|
| Total price observations | 284 |
| Observations per city/date | 33-36 |
| Foods consistently present in both markets on all four dates | 33 |
| Fruit among those shared foods | 15 |
| Vegetables among those shared foods | 12 |
| Tubers and plantains among those shared foods | 6 |

## A preview of the actual table

| Date | City | Food | Food group | Average wholesale price (COP/kg) |
|---|---|---|---|---:|
| 2025-02-12 | Bogota | Aguacate | Fruit | 8,688 |
| 2025-02-12 | Bogota | Banano | Fruit | 2,925 |
| 2025-02-12 | Bogota | Coco | Fruit | 8,142 |
| 2025-02-12 | Bogota | Granadilla | Fruit | 11,347 |
| 2025-02-12 | Bogota | Guayaba | Fruit | 2,188 |
| 2025-02-12 | Bogota | Limon Tahiti | Fruit | 2,491 |

## Selected fresh-food reference basket

The selected foods are: cebolla cabezona blanca, zanahoria, tomate, ahuyama, banano, naranja, guayaba, aguacate, yuca, and chócolo mazorca.

Each food contributes one kilogram because every SIPSA price is reported per kilogram. This is an **equal-weight reference basket** for comparing markets and dates, not a consumer food basket and not CoHD.

| Date | Bogota total (COP) | Medellin total (COP) | Bogota higher by |
|---|---:|---:|---:|
| 2025-02-12 | 29,177 | 24,222 | 20.5% |
| 2025-05-14 | 32,306 | 29,186 | 10.7% |
| 2025-08-13 | 32,646 | 28,230 | 15.6% |
| 2025-11-12 | 33,315 | 27,392 | 21.6% |

## What happens next

1. Graph market and seasonal differences in the selected reference basket.
2. Inspect which foods drive the difference on each date.
3. Use national CoHD, nutrition, production diversity, and import-reliance data to explain the larger context - without claiming that this pilot calculates CoHD.

## Files to open

| If you want to... | Open this file |
|---|---|
| See the full clean table | `data/processed/colombia_sipsa_pilot.csv` |
| See the selected basket totals | `data/processed/reference_basket_totals.csv` |
| See or change the selected basket | `data/basket_definition.csv` |
| See the original official source workbooks | `data/raw/` |
| See how the table was created | `src/build_colombia_sipsa_pilot.py` |
