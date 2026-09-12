window.MONITOR_DATA = {
  sourceLabel: "DANE SIPSA wholesale market-price pilot; ICBF TCAC 2018 nutrition profiles",
  actions: [
    {date:"2025-02-12", market:"Bogotá", higher:"Zanahoria", higherPrice:2177, lower:"Ahuyama", lowerPrice:1675, savings:502},
    {date:"2025-02-12", market:"Medellín", higher:"Ahuyama", higherPrice:1025, lower:"Zanahoria", lowerPrice:1022, savings:3},
    {date:"2025-05-14", market:"Bogotá", higher:"Ahuyama", higherPrice:1875, lower:"Zanahoria", lowerPrice:1750, savings:125},
    {date:"2025-05-14", market:"Medellín", higher:"Ahuyama", higherPrice:925, lower:"Zanahoria", lowerPrice:911, savings:14},
    {date:"2025-08-13", market:"Bogotá", higher:"Zanahoria", higherPrice:4271, lower:"Ahuyama", lowerPrice:2913, savings:1358},
    {date:"2025-08-13", market:"Medellín", higher:"Zanahoria", higherPrice:1972, lower:"Ahuyama", lowerPrice:1750, savings:222},
    {date:"2025-11-12", market:"Bogotá", higher:"Zanahoria", higherPrice:2000, lower:"Ahuyama", lowerPrice:1900, savings:100},
    {date:"2025-11-12", market:"Medellín", higher:"Zanahoria", higherPrice:2167, lower:"Ahuyama", lowerPrice:950, savings:1217}
  ],
  nutrients: {
    "Zanahoria": {energy:47, protein:0.7, fiber:0.8, iron:0.4, calcium:27, vitaminA:1318, vitaminC:3, tcac:"B110 — Zanahoria, sin cáscara, cruda"},
    "Ahuyama": {energy:30, protein:0.8, fiber:1.1, iron:0.8, calcium:20, vitaminA:1775, vitaminC:9, tcac:"B006 — Ahuyama, cruda"}
  },
  rule: {
    role:"Orange vegetable role",
    vitaminAThreshold:1000,
    fiberThreshold:0.8,
    statement:"Potential lower-cost alternative: the lower-priced food meets the pilot role guardrails for vitamin A and fibre. This is a decision-support prompt, not dietary advice."
  },
  threeMarket: {
    foodCount: 8,
    excludedFoods: ["Aguacate", "Guayaba"],
    totals: [
      {date:"2025-02-12", city:"Bogotá", total:18301}, {date:"2025-02-12", city:"Medellín", total:15297}, {date:"2025-02-12", city:"Montería", total:14084},
      {date:"2025-05-14", city:"Bogotá", total:18447}, {date:"2025-05-14", city:"Medellín", total:17461}, {date:"2025-05-14", city:"Montería", total:15686},
      {date:"2025-08-13", city:"Bogotá", total:22357}, {date:"2025-08-13", city:"Medellín", total:18555}, {date:"2025-08-13", city:"Montería", total:17343},
      {date:"2025-11-12", city:"Bogotá", total:18895}, {date:"2025-11-12", city:"Medellín", total:14717}, {date:"2025-11-12", city:"Montería", total:15236}
    ]
  },
  nigeriaValidation: {
    sourceLabel: "Nigeria National Bureau of Statistics, Selected Food Price Watch, Zone All item sheets",
    geographyLevel: "Zone-level monthly average",
    ranges: [
      {date:"2026-03-01", item:"Beans Brown", unit:"1 kg", low:851.11, lowZone:"North West", high:1770.57, highZone:"South West", gap:919.46, gapPct:108.0},
      {date:"2026-04-01", item:"Beans Brown", unit:"1 kg", low:871.79, lowZone:"North East", high:1787.09, highZone:"South West", gap:915.30, gapPct:105.0},
      {date:"2026-05-01", item:"Beans Brown", unit:"1 kg", low:876.46, lowZone:"North East", high:1790.71, highZone:"South West", gap:914.25, gapPct:104.3},
      {date:"2026-03-01", item:"Garri white", unit:"1 kg", low:670.16, lowZone:"North Central", high:942.68, highZone:"South South", gap:272.52, gapPct:40.7},
      {date:"2026-04-01", item:"Garri white", unit:"1 kg", low:673.88, lowZone:"North Central", high:944.58, highZone:"South East", gap:270.70, gapPct:40.2},
      {date:"2026-05-01", item:"Garri white", unit:"1 kg", low:676.21, lowZone:"North Central", high:947.08, highZone:"South East", gap:270.86, gapPct:40.1}
    ]
  }
};
