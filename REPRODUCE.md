# Reproduce the Hoos' Cooking pilot

The public dashboard is intentionally static so reviewers can open it without installing software. The analysis notebooks below recreate the tables behind its Colombia and Nigeria validation sections.

## Quick review

1. Open the [public dashboard](https://gmancuso82.github.io/women-in-data-2026-datathon/).
2. Open the [country-run collection and review prototype](https://gmancuso82.github.io/women-in-data-2026-datathon/data-collection-pipeline/).
3. Read [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) for methods, evidence, and limitations.

## Re-run the analysis

From the repository root, open either notebook and choose **Run All**:

1. [`colombia_sipsa_pilot/notebooks/01_colombia_price_gap_and_swap_analysis.ipynb`](colombia_sipsa_pilot/notebooks/01_colombia_price_gap_and_swap_analysis.ipynb)
2. [`colombia_sipsa_pilot/notebooks/02_nigeria_portability_validation.ipynb`](colombia_sipsa_pilot/notebooks/02_nigeria_portability_validation.ipynb)

Both notebooks use the already-versioned processed CSV files. Their sources, methods, and interpretation boundaries are documented in [`colombia_sipsa_pilot/README.md`](colombia_sipsa_pilot/README.md), [`THREE_MARKET_VALIDATION.md`](colombia_sipsa_pilot/THREE_MARKET_VALIDATION.md), and [`NIGERIA_NBS_VALIDATION.md`](colombia_sipsa_pilot/NIGERIA_NBS_VALIDATION.md).

## Important boundaries

- Colombia data are DANE SIPSA wholesale market-price observations, not household retail prices or a subnational Cost of a Healthy Diet calculation.
- The carrot–ahuyama comparison is a transparent, nutrition-aware review prompt—not automatic dietary or procurement advice.
- Nigeria is a portability check using NBS zone-level monthly averages. It is price-only until nutrition matches have been reviewed.
- The collection pipeline is a proof of concept. Automatically moving approved intake records into the dashboard is a future integration step.
