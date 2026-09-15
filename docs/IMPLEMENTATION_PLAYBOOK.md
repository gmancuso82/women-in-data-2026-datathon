# Hoos' Cooking implementation playbook

## Purpose

Hoos' Cooking is a **country-owned pathway** from local food-price observations to nutrition-aware, human-reviewed decision support. It is designed to complement—not replace—national Cost and Affordability of a Healthy Diet monitoring.

The pilot begins with the macro problem of healthy-diet affordability and works at the micro level: local markets, food preferences, geography, collection methods, and program needs can differ substantially within and across countries.

## Who uses it

| Role | Responsibility |
| --- | --- |
| Local market enumerator or food hub | Records a price observation using the digital or printable form. |
| Designated reviewer | Checks extracted fields, corrects errors, and approves or rejects the record. |
| Nutrition/program reviewer | Validates local food-role matches and considers diet, culture, availability, and program requirements. |
| Government or food-program analyst | Reviews location/date price signals and scenario outputs as one input to a decision. |

## The five-step workflow

### 1. Define a locally meaningful basket

Start with foods that are locally relevant, their market units, and the decision question (for example, school meals, maternal nutrition programming, or emergency procurement). Do not assume a food role or nutrition match transfers unchanged from another country.

### 2. Collect local price observations

Use the [collection and review prototype](https://gmancuso82.github.io/women-in-data-2026-datathon/data-collection-pipeline/) in the format that fits local capacity:

- digital intake where devices and connectivity are available;
- printable paper forms where they are not;
- scan/photo extraction for paper submissions; and
- a human review step before a record is approved.

The pipeline is a proof of concept. It demonstrates a locally run collection process; it is not presented as a deployed national data system.

### 3. Review and retain context

Every approved record should retain its collection date, location/geography level, item name, unit, currency, source, and review status. This prevents misleading comparisons across cities, countries, retail/wholesale sources, or incompatible units.

### 4. Refresh the monitoring dataset

Approved records can be exported to the monitoring schema and added to a local dashboard refresh. This project demonstrates the two layers separately:

- the current [dashboard](https://gmancuso82.github.io/women-in-data-2026-datathon/) validates the decision layer with historical Colombia data; and
- the collection pipeline validates the local intake, extraction, and review path.

Automatically moving approved collection records into the dashboard is the next integration step—not a completed claim of this prototype.

### 5. Generate a reviewable action prompt

The dashboard can surface a price difference by food, locality, and date. A nutrition-aware lower-cost candidate should appear only when:

1. the food role and nutrition profile have been reviewed for the local context;
2. price and nutrition units describe comparable edible amounts;
3. the display makes nutrition tradeoffs visible; and
4. a qualified human reviews the output before any program or policy decision.

## What the current pilot demonstrates

- **Colombia:** DANE SIPSA wholesale observations for Bogotá, Medellín, and Montería on four sampled 2025 dates, including an eight-food shared basket directly comparable across all three markets.
- **Nutrition-aware review:** a transparent carrot–ahuyama orange-vegetable comparison using verified ICBF TCAC profiles. The dashboard shows nutrients per 100 g and documented vitamin A/fibre guardrails.
- **Nigeria portability:** a separate Nigeria NBS zone-level sample that preserves country, currency, geography, source, unit, and cadence. It is intentionally price-only until nutrition profiles are reviewed.
- **Planning scenario:** a user-entered quantity can scale an observed per-kilogram price difference into a potential gross price difference. It does not estimate full procurement savings.

## Guardrails

- Wholesale prices are not household retail prices and are not a subnational Cost of a Healthy Diet estimate.
- Observed differences do not diagnose weather, shortages, logistics, or policy causes.
- A lower-cost candidate is not an automatic food substitution, dietary recommendation, or procurement instruction.
- Price-only planning scenarios exclude availability, yields, transport, contracts, waste, and menu/diet planning.
- Local ownership requires governance, retention rules, privacy controls, local catalog validation, multilingual testing, and auditability before production use.

## Reviewer links

- [Live decision-support dashboard](https://gmancuso82.github.io/women-in-data-2026-datathon/)
- [Live collection and review prototype](https://gmancuso82.github.io/women-in-data-2026-datathon/data-collection-pipeline/)
- [Reproduction guide](../REPRODUCE.md)
- [Project scope and evidence](PROJECT_SCOPE.md)
