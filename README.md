# Hoos' Cooking

**A country-owned pathway from local food-price observations to nutrition-aware decision support.**

Hoos' Cooking connects two complementary prototypes:

1. **Local collection and review.** A country can collect food-price observations with a digital form or a printable paper form, extract fields from scanned paper submissions, and require human review before records are approved.
2. **Local monitoring and decision support.** The dashboard uses reviewed, structured data to compare food prices across locations and dates, surface lower-cost candidates, and show nutrition guardrails before any human decision.

The project starts with the macro context of healthy-diet affordability and moves to the micro reality of local markets, food culture, geography, seasonal conditions, and technology access.

The motivation is maternal and child nutrition: reliable access to affordable, nutrient-rich foods is one important food-access pathway, alongside health, sanitation, caregiving, and household income.

## Live prototype

[Open the public dashboard](https://gmancuso82.github.io/women-in-data-2026-datathon/)

[Open the data-collection pipeline hub](https://gmancuso82.github.io/women-in-data-2026-datathon/data-collection-pipeline/pipeline_hub.1.1.html)

The current dashboard demonstrates the decision layer with historical, official data. The collection pipeline demonstrates how countries can build a more timely, locally owned source of reviewed records. Connecting approved pipeline records to automated dashboard refreshes is a next integration step.

## What the pilot demonstrates

### Colombia market comparison

- Official DANE SIPSA wholesale market-price observations
- Bogotá, Medellín, and Montería
- Four sampled dates in 2025
- An eight-food shared basket directly comparable across all three markets
- A transparent price-and-nutrition comparison for the verified carrot and ahuyama orange-vegetable role
- An interactive procurement-scenario calculator that scales the selected per-kilogram price difference to a user-entered quantity, while keeping its price-only boundary explicit

These are wholesale price observations and an equal-weight reference basket. They are **not** household retail prices or a subnational Cost of a Healthy Diet calculation.

### Nigeria portability check

- Nigeria National Bureau of Statistics Selected Food Price Watch
- Zone-level monthly averages for March through May 2026
- Beans Brown and Garri white, both reported on a 1 kg basis

This check shows the monitoring structure can retain a different country, currency, source format, and geography level. It remains price-only until nutrition profiles are reviewed.

### Local collection pipeline

The collection pipeline supports digital and printable-paper intake, scan/photo extraction, human review, and a correction-feedback loop. It is a proof of concept for a country-run data-collection process; it does not claim a fully deployed live national system.

## Decision-support guardrails

- The dashboard does not diagnose shortages, weather events, or supply-chain causes.
- A lower-cost candidate is not an automatic food substitution or dietary recommendation.
- The procurement scenario is a gross price-difference estimate; it excludes availability, yields, transport, contracts, and dietary planning.
- Nutrition and program experts remain responsible for policy and program decisions.
- Foods without verified nutrition matches stay in a review state rather than generating a recommendation.

## Repository guide

- [`data-collection-pipeline/`](data-collection-pipeline/) — country-run collection, extraction, review, and feedback-loop prototype.
- [`colombia_sipsa_pilot/`](colombia_sipsa_pilot/) — reproducible Colombia and Nigeria validation data, scripts, and the public dashboard.
- [`colombia_sipsa_pilot/notebooks/`](colombia_sipsa_pilot/notebooks/) — two clean, runnable analysis notebooks for Colombia evidence and Nigeria portability validation.
- [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) — methods, evidence, limitations, and next integration step.
- [`docs/IMPLEMENTATION_PLAYBOOK.md`](docs/IMPLEMENTATION_PLAYBOOK.md) — country-owned collection-to-decision workflow and operational guardrails.
- [`docs/PRESENTATION_SCRIPT.md`](docs/PRESENTATION_SCRIPT.md) — competition presentation talk track and demo sequence.
- [`REPRODUCE.md`](REPRODUCE.md) — quick reviewer path for the live prototypes and analysis notebooks.

## Core sources

- DANE SIPSA wholesale market-price workbooks, Colombia
- Nigeria National Bureau of Statistics Selected Food Price Watch, March-May 2026
- Instituto Colombiano de Bienestar Familiar, Tabla de Composición de Alimentos Colombianos 2018
- FAOSTAT Cost and Affordability of a Healthy Diet context
