const data = window.MONITOR_DATA;
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
const formatDate = (date) => new Intl.DateTimeFormat("en-US", { month:"short", day:"numeric", year:"numeric", timeZone:"UTC" }).format(new Date(`${date}T00:00:00Z`));
const unique = (items) => [...new Set(items)];

const marketSelect = document.querySelector("#market-select");
const dateSelect = document.querySelector("#date-select");

function populateSelect(select, values) {
  select.innerHTML = values.map((value) => `<option value="${value}">${value.includes("-") ? formatDate(value) : value}</option>`).join("");
}

function nutrientRows(higher, lower) {
  const metrics = [
    ["Energy", "energy", "kcal"], ["Protein", "protein", "g"], ["Fibre", "fiber", "g"],
    ["Iron", "iron", "mg"], ["Calcium", "calcium", "mg"], ["Vitamin A", "vitaminA", "ER"], ["Vitamin C", "vitaminC", "mg"]
  ];
  return metrics.map(([label, key, unit]) => {
    const direction = lower[key] > higher[key] ? "better" : lower[key] < higher[key] ? "tradeoff" : "";
    return `<div class="nutrition-row"><span>${label}</span><strong>${higher[key]} ${unit}</strong><strong class="${direction}">${lower[key]} ${unit}</strong></div>`;
  }).join("");
}

function renderAction() {
  const action = data.actions.find((row) => row.market === marketSelect.value && row.date === dateSelect.value);
  const higherNutrition = data.nutrients[action.higher];
  const lowerNutrition = data.nutrients[action.lower];
  document.querySelector("#action-title").textContent = "Potential lower-cost alternative";
  document.querySelector("#action-copy").textContent = `${action.lower} meets the pilot orange-vegetable guardrails and costs less than ${action.higher} in ${action.market} on ${formatDate(action.date)}.`;
  document.querySelector("#higher-food").textContent = action.higher;
  document.querySelector("#higher-price").textContent = `${money.format(action.higherPrice)} / kg`;
  document.querySelector("#lower-food").textContent = action.lower;
  document.querySelector("#lower-price").textContent = `${money.format(action.lowerPrice)} / kg`;
  document.querySelector("#saving").textContent = money.format(action.savings);
  document.querySelector("#nutrition-table").innerHTML = `<div class="nutrition-row"><span></span><strong>${action.higher}</strong><strong>${action.lower}</strong></div>${nutrientRows(higherNutrition, lowerNutrition)}`;
}

function renderThreeMarketValidation() {
  const rows = data.threeMarket.totals
    .filter((row) => row.date === dateSelect.value)
    .sort((a, b) => a.total - b.total);
  const lowest = rows[0].total;
  const highest = rows[rows.length - 1].total;
  document.querySelector("#shared-basket-copy").textContent =
    `${data.threeMarket.foodCount}-food shared basket on ${formatDate(dateSelect.value)}. ` +
    `${data.threeMarket.excludedFoods.join(" and ")} are excluded because they were not observed in every market on every date.`;
  document.querySelector("#market-total-cards").innerHTML = rows.map((row) => {
    const position = row.total === lowest ? "lowest" : row.total === highest ? "highest" : "middle";
    const label = position === "lowest" ? "Lowest observed total" : position === "highest" ? "Highest observed total" : "Middle observed total";
    return `<article class="market-total-card ${position}"><span>${row.city}</span><strong>${money.format(row.total)}</strong><small>${label}</small></article>`;
  }).join("");
}

function renderChart() {
  const max = Math.max(...data.actions.map((row) => row.savings));
  const byDate = unique(data.actions.map((row) => row.date));
  document.querySelector("#saving-chart").innerHTML = byDate.map((date) => {
    const rows = data.actions.filter((row) => row.date === date);
    const bars = rows.map((row) => `<div class="bar ${row.market === "Medellín" ? "medellin" : ""}" style="height:${Math.max(4, row.savings / max * 150)}px"><span>${row.savings.toLocaleString()}</span></div>`).join("");
    return `<div class="chart-group">${bars}<div class="bar-label">${formatDate(date)}<br>Bogotá / Medellín</div></div>`;
  }).join("");
}

populateSelect(marketSelect, unique(data.actions.map((row) => row.market)));
populateSelect(dateSelect, unique(data.actions.map((row) => row.date)));
document.querySelector("#observation-count").textContent = data.actions.length;
document.querySelector("#largest-saving").textContent = money.format(Math.max(...data.actions.map((row) => row.savings)));
document.querySelector("#rule-statement").textContent = data.rule.statement;
document.querySelector("#source-label").textContent = data.sourceLabel;
marketSelect.addEventListener("change", renderAction);
dateSelect.addEventListener("change", () => {
  renderAction();
  renderThreeMarketValidation();
});
renderAction();
renderThreeMarketValidation();
renderChart();
