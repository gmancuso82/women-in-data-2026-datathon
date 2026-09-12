# Nigeria NBS portability validation

## Purpose

This is a **source-format and geography-label validation**, not a second version of the Colombia market analysis. It checks whether the monitor's underlying schema can retain a different country's source, currency, geography level, product, unit, and collection month without mixing it into the Colombia SIPSA evidence.

## Source and scope

The Nigeria National Bureau of Statistics (NBS) publishes a monthly *Selected Food Price Watch*. The audit uses the `Zone All item` sheet from March, April, and May 2026 releases. It contains zone-level averages for six zones, not city market observations.

The processed sample keeps two foods whose reports explicitly state a 1 kg basis:

- `Beans Brown`
- `Garri white`

## Verified pattern

For the same food and unit, the high-to-low zone gap persisted across all three months:

| Food | March 2026 | April 2026 | May 2026 |
| --- | ---: | ---: | ---: |
| Beans Brown (1 kg) | NGN 919 | NGN 915 | NGN 914 |
| Garri white (1 kg) | NGN 273 | NGN 271 | NGN 271 |

This supports the narrower claim that source and geography matter when interpreting food prices. It does **not** establish causes of the price differences, household affordability, or a local retail CoHD.

## Guardrail

The Nigeria food labels do not yet have reviewed nutrition profiles in this pilot. The monitor must display `Price received; nutrition match still needs review` and must not generate a food-substitution recommendation from this validation sample.

## Reproducibility

`src/build_nigeria_nbs_validation.py` produces:

- `data/processed/nigeria_nbs_zone_prices_march_may_2026.csv`
- `data/processed/nigeria_nbs_zone_price_ranges_march_may_2026.csv`

Source releases: [March 2026](https://microdata.nigerianstat.gov.ng/index.php/catalog/162/download/1401), [April 2026](https://microdata.nigerianstat.gov.ng/index.php/catalog/162/download/1415), [May 2026](https://microdata.nigerianstat.gov.ng/index.php/catalog/162/download/1427).
