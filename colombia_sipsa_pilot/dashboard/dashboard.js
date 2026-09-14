const data = window.MONITOR_DATA;
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
const formatDate = (date) => new Intl.DateTimeFormat("en-US", { month:"short", day:"numeric", year:"numeric", timeZone:"UTC" }).format(new Date(`${date}T00:00:00Z`));
const unique = (items) => [...new Set(items)];

const marketSelect = document.querySelector("#market-select");
const dateSelect = document.querySelector("#date-select");
const quantityInput = document.querySelector("#quantity-input");

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
  renderImpactCalculator(action);
}

function planningQuantity() {
  const entered = Number(quantityInput.value);
  const quantity = Number.isFinite(entered) ? Math.min(100000, Math.max(1, Math.round(entered))) : 1;
  quantityInput.value = quantity;
  return quantity;
}

function renderImpactCalculator(action) {
  const quantity = planningQuantity();
  const grossDifference = action.savings * quantity;
  document.querySelector("#impact-copy").textContent =
    `For ${quantity.toLocaleString()} market kg of ${action.higher}, the selected ${action.market} observation suggests ${action.lower} could have a lower observed commodity price.`;
  document.querySelector("#impact-saving").textContent = money.format(grossDifference);
  document.querySelector("#impact-unit").textContent = `${money.format(action.savings)} per kg × ${quantity.toLocaleString()} market kg`;
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
    const bars = rows.map((row) => `<div class="bar ${row.market.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")}" style="height:${Math.max(4, row.savings / max * 150)}px"><span>${row.savings.toLocaleString()}</span></div>`).join("");
    return `<div class="chart-group">${bars}<div class="bar-label">${formatDate(date)}<br>Bogotá · Medellín · Montería</div></div>`;
  }).join("");
}

const naira = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 });
const nigeriaSelect = document.querySelector("#nigeria-item-select");

function renderNigeriaValidation() {
  const rows = data.nigeriaValidation.ranges.filter((row) => row.item === nigeriaSelect.value);
  document.querySelector("#nigeria-ranges").innerHTML = rows.map((row) => `
    <article class="nigeria-range">
      <time>${formatDate(row.date)}</time>
      <strong>${naira.format(row.gap)} gap</strong>
      <p>Low: ${naira.format(row.low)} in ${row.lowZone}</p>
      <p>High: ${naira.format(row.high)} in ${row.highZone}</p>
      <p class="subtle">${row.gapPct.toFixed(1)}% of the lowest zone average for ${row.unit}</p>
    </article>`).join("");
}

populateSelect(marketSelect, unique(data.actions.map((row) => row.market)));
populateSelect(dateSelect, unique(data.actions.map((row) => row.date)));
populateSelect(nigeriaSelect, unique(data.nigeriaValidation.ranges.map((row) => row.item)));
document.querySelector("#observation-count").textContent = data.actions.length;
document.querySelector("#largest-saving").textContent = money.format(Math.max(...data.actions.map((row) => row.savings)));
document.querySelector("#rule-statement").textContent = data.rule.statement;
document.querySelector("#source-label").textContent = data.sourceLabel;
marketSelect.addEventListener("change", renderAction);
dateSelect.addEventListener("change", () => {
  renderAction();
  renderThreeMarketValidation();
});
nigeriaSelect.addEventListener("change", renderNigeriaValidation);
quantityInput.addEventListener("input", renderAction);
document.querySelectorAll("[data-quantity]").forEach((button) => {
  button.addEventListener("click", () => {
    quantityInput.value = button.dataset.quantity;
    renderAction();
  });
});
renderAction();
renderThreeMarketValidation();
renderChart();
renderNigeriaValidation();
