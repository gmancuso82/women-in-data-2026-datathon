# Local Healthy Food Swap Monitor

The dashboard is a static, browser-based decision-support prototype published through GitHub Pages.

## What is interactive

- Select a Colombian locality and collection date to update the lower-cost orange-vegetable comparison and its nutrition tradeoff.
- Review the three-market shared-basket totals for the selected date.
- Select a Nigeria food to view zone-level price ranges across three monthly reports.

## What the dashboard demonstrates

The Colombia section uses official DANE SIPSA **wholesale** price observations. It is a local market-price proxy, not a household retail Cost of a Healthy Diet calculation. The nutrition view compares the verified raw edible-portion profiles for carrot and ahuyama and explains why a lower-cost candidate appears.

The Nigeria section validates portability across a different country, currency, source format, and geography level. It is price-only because those food labels do not yet have reviewed nutrition profiles.

## Guardrails

- The dashboard does not diagnose the cause of a price difference.
- It does not make automatic substitutions or provide dietary advice.
- Fresh corn is blocked from nutrition claims until whole-cob market-price units and edible-kernel nutrition units are reconciled.
- New local observations from the separate collection pipeline are not automatically ingested into this static prototype yet.

## Local use

Open `index.html` in a browser. GitHub Pages publishes the same static prototype for public review.

