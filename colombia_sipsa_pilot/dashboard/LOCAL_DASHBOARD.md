# Local dashboard

Open `index.html` in a web browser to use the current prototype. Choose a locality and collection date to inspect the price action and the nutrition tradeoff.

The dashboard displays a **price comparison**, not cost per nutrient. It blocks fresh-corn recommendations because the market-product and edible-nutrition units have not yet been reconciled.

Before presenting the pilot, rerun these two scripts after changing price or nutrition data:

```bash
python src/build_orange_vegetable_actions.py
```

Then update the small `dashboard_data.js` dataset or replace it with an automated export step.
