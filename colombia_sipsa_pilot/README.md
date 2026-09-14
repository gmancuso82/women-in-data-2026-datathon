# Colombia SIPSA and Nigeria monitoring pilot

This folder contains the reproducible data and dashboard for the Hoos' Cooking monitoring prototype.

## Colombia market-price validation

The Colombia analysis converts four official DANE SIPSA workbooks into a tidy wholesale market-price table for Bogotá, Medellín, and Montería on 12 February, 14 May, 13 August, and 12 November 2025.

The three-market comparison uses an equal-weight basket of eight foods observed in every market on every sampled date. It supports the narrow finding that food-price differences vary by item, city, and date. It does not establish causes, retail household affordability, or a subnational Cost of a Healthy Diet.

## Nutrition-aware action prompt

The dashboard includes one verified pilot role: carrot and ahuyama as orange vegetables. A lower-cost candidate appears only when the item meets the documented vitamin A and fibre guardrails. The dashboard shows the nutrition tradeoff and requires human review; it does not provide dietary advice or an automatic substitution. Its quantity calculator translates the selected per-kilogram difference into a potential gross price difference for a planning quantity; it excludes availability, yields, transport, contracts, and diet planning.

## Nigeria portability validation

The Nigeria National Bureau of Statistics sample is intentionally separate from the Colombia evidence. It uses zone-level monthly averages for Beans Brown and Garri white from March through May 2026 to demonstrate that the monitoring structure can retain a different country, currency, source, geography, and unit without making unsupported comparisons.

## Important boundary

The public dashboard is a historical-data decision-support prototype. The separate `data-collection-pipeline/` folder demonstrates a country-run process for collecting and reviewing more timely local records. Automated transfer of approved collection records into the dashboard is a next integration step.

## Key files

- [`THREE_MARKET_VALIDATION.md`](THREE_MARKET_VALIDATION.md) — three-city shared-basket evidence and interpretation limits.
- [`NIGERIA_NBS_VALIDATION.md`](NIGERIA_NBS_VALIDATION.md) — portability validation and price-only guardrail.
- [`data/nutrition_lookup.csv`](data/nutrition_lookup.csv) — nutrition match status and source notes.
- [`dashboard/`](dashboard/) — static dashboard published through GitHub Pages.
- [`src/`](src/) — reproducible data-build and analysis scripts.
