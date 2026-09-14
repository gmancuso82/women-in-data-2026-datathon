# Project scope and evidence

## Project question

Can standardized local food-price observations reveal location and seasonal differences that a national annual healthy-diet estimate can hide, while preserving nutrition and human-review guardrails?

## Two connected prototypes

**Collection pipeline.** The `data-collection-pipeline/` prototype accepts digital or printable-paper forms, extracts fields from scanned paper records, requires human review, and uses corrections as future classifier labels. It is designed to be country-run.

**Decision dashboard.** The public dashboard demonstrates how reviewed records can be compared by location and date, then paired with a narrow, verified nutrition-role comparison. It currently uses historical validation data rather than a live automated feed from the collection pipeline.

## Evidence used today

### Colombia

Four official DANE SIPSA collection dates in 2025 are used to compare Bogotá, Medellín, and Montería. The direct three-market analysis uses eight foods present in all three markets at all four dates. SIPSA reports wholesale market prices, so this is not a retail household affordability estimate or a Cost of a Healthy Diet calculation.

### Nigeria

Three Nigeria National Bureau of Statistics Selected Food Price Watch releases from 2026 are used as a portability check. The dashboard retains the zone-level geography, Nigerian naira currency, monthly cadence, food name, and 1 kg unit. It does not compare the Nigeria series with Colombia or issue nutrition recommendations for it.

### Nutrition

Carrot and ahuyama have verified ICBF TCAC raw edible-portion matches in the pilot. The dashboard displays energy, protein, fibre, iron, calcium, vitamin A, and vitamin C per 100 g and applies a documented orange-vegetable role guardrail. It presents a reviewable candidate, not a claim that foods are nutritionally identical.

## Interpretation limits

- Price differences are observations, not causal evidence about transport, weather, shortages, or policy.
- A food-price signal can prompt investigation; it is not a diagnosis of a disruption.
- A lower-cost candidate is not medical, dietary, or procurement advice.
- The dashboard does not currently store or automatically ingest new collection submissions.

## Next integration step

Export a reviewer-approved record from the collection pipeline to the monitoring schema, retain source and review metadata, and refresh the dashboard from that verified dataset. Any production deployment would also require country governance, retention rules, privacy controls, local catalog validation, multilingual testing, and auditability.

