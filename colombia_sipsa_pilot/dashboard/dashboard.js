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

// Local upload prototype -----------------------------------------------------
// These fields are deliberately stored only in this browser after the user
// approves them. The original PDF never leaves the device or enters storage.
const uploadInput = document.querySelector("#price-sheet-input");
const uploadStatus = document.querySelector("#upload-status");
const uploadReview = document.querySelector("#upload-review");
const reviewRows = document.querySelector("#review-rows");
const reviewMethod = document.querySelector("#review-method");
const reviewHelp = document.querySelector("#review-help");
const savedSummary = document.querySelector("#saved-upload-summary");
const localStorageKey = "sipsa-pilot-local-price-observations-v1";
let currentUpload = null;

const nutritionProfiles = new Set(["zanahoria", "ahuyama", "yuca"]);
const normalizedFood = (value = "") => value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9 ]/g, "").replace(/\s+/g, " ").trim();
const nutritionStatus = (food) => nutritionProfiles.has(normalizedFood(food)) ? "Verified profile available" : "Needs nutrition review";
const getSavedRows = () => {
  try { return JSON.parse(localStorage.getItem(localStorageKey) || "[]"); }
  catch { return []; }
};
const saveRows = (rows) => localStorage.setItem(localStorageKey, JSON.stringify(rows));

function renderSavedSummary() {
  const saved = getSavedRows();
  savedSummary.textContent = saved.length
    ? `${saved.length} reviewed observation${saved.length === 1 ? "" : "s"} saved on this device. Download or clear them below.`
    : "No reviewed observations are saved on this device.";
}

function textFromPdfPage(content) {
  let text = "";
  for (const item of content.items) {
    text += item.str || "";
    text += item.hasEOL ? "\n" : " ";
  }
  return text;
}

function firstMatch(text, expressions) {
  for (const expression of expressions) {
    const match = text.match(expression);
    if (match?.[1]) return match[1].trim();
  }
  return "";
}

function parseCop(value) {
  const cleaned = String(value || "").replace(/[^\d,.-]/g, "");
  if (!cleaned) return "";
  const compact = cleaned.replace(/\.(?=\d{3}(?:\D|$))/g, "").replace(/,/g, ".");
  const number = Number(compact);
  return Number.isFinite(number) ? Math.round(number) : "";
}

function parsePriceSheet(text) {
  const locality = firstMatch(text, [/(?:locality|localidad|city|ciudad)\s*[:\-]\s*([^\n]+)/i]);
  const market = firstMatch(text, [/(?:market|mercado|source|fuente)\s*[:\-]\s*([^\n]+)/i]);
  const rawDate = firstMatch(text, [/(?:collection\s*date|fecha\s*(?:de\s*)?(?:recolecci[oó]n)?)\s*[:\-]\s*([^\n]+)/i]);
  const dateMatch = rawDate.match(/(20\d{2})[-\/](\d{1,2})[-\/](\d{1,2})/);
  const collectionDate = dateMatch ? `${dateMatch[1]}-${dateMatch[2].padStart(2, "0")}-${dateMatch[3].padStart(2, "0")}` : "";
  const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const rows = [];
  for (const line of lines) {
    const columns = line.split(/\s*[|]\s*/).map((value) => value.trim());
    if (columns.length >= 3 && !/food|alimento|price|precio/i.test(columns[0])) {
      const price = parseCop(columns[2]);
      if (price) rows.push({ food: columns[0], unit: columns[1], price });
    }
  }
  // Many ordinary office PDFs expose table cells as consecutive text lines
  // rather than a true table. Recognize the common Food / Unit / Price rhythm.
  if (!rows.length) {
    const unitPattern = /^(?:COP\s*\/?\s*kg|COP\/kg|kg|kilogramo)$/i;
    for (let index = 0; index + 2 < lines.length; index += 1) {
      const food = lines[index];
      const unit = lines[index + 1];
      const price = parseCop(lines[index + 2]);
      if (unitPattern.test(unit) && price && !/food|alimento|price|precio/i.test(food)) {
        rows.push({ food, unit, price });
        index += 2;
      }
    }
  }
  if (!rows.length) {
    const pattern = /([A-Za-zÁÉÍÓÚÑáéíóúÜü][A-Za-zÁÉÍÓÚÑáéíóúÜü\s]{2,}?)\s+(?:COP\s*\/?\s*kg|COP\/kg|kg|kilogramo)\s+\$?\s*([\d.,]+)/gi;
    let match;
    while ((match = pattern.exec(text))) rows.push({ food: match[1].trim(), unit: "COP/kg", price: parseCop(match[2]) });
  }
  return { locality, market, collectionDate, rows: rows.slice(0, 20) };
}

function renderReview(parsed, method, filename) {
  currentUpload = { parsed, method, filename };
  document.querySelector("#review-locality").value = parsed.locality;
  document.querySelector("#review-date").value = parsed.collectionDate;
  document.querySelector("#review-market").value = parsed.market;
  reviewMethod.textContent = method;
  reviewRows.innerHTML = parsed.rows.length ? parsed.rows.map((row, index) => {
    const status = nutritionStatus(row.food);
    const verified = status.startsWith("Verified");
    return `<tr data-row="${index}"><td><input data-field="food" value="${escapeHtml(row.food)}" /></td><td><input data-field="unit" value="${escapeHtml(row.unit || "COP/kg")}" /></td><td><input data-field="price" type="number" min="0" step="1" value="${row.price || ""}" /></td><td><span class="nutrition-pill ${verified ? "verified" : "review"}">${status}</span></td></tr>`;
  }).join("") : `<tr><td><input data-field="food" placeholder="Food name" /></td><td><input data-field="unit" value="COP/kg" /></td><td><input data-field="price" type="number" min="0" step="1" placeholder="Price" /></td><td><span class="nutrition-pill review">Needs nutrition review</span></td></tr>`;
  uploadReview.hidden = false;
  reviewHelp.textContent = parsed.rows.length
    ? "Review and correct the extracted fields. Required before saving: locality, collection date, food name, price, and unit. The PDF itself is not retained."
    : "The file was received, but no price rows could be reliably extracted. Enter the required fields below to preserve the observation for review.";
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>'"]/g, (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"})[character]);
}

async function ocrFirstPage(pdf) {
  const page = await pdf.getPage(1);
  const viewport = page.getViewport({ scale: 2 });
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(viewport.width);
  canvas.height = Math.ceil(viewport.height);
  await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
  if (!window.Tesseract) throw new Error("The optional local OCR library did not load.");
  const result = await window.Tesseract.recognize(canvas, "eng", { logger: (message) => {
    if (message.status === "recognizing text" && typeof message.progress === "number") uploadStatus.textContent = `Reading scanned PDF… ${Math.round(message.progress * 100)}%`;
  }});
  return result.data.text || "";
}

uploadInput.addEventListener("change", async () => {
  const file = uploadInput.files?.[0];
  if (!file) return;
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    uploadStatus.textContent = "Please choose a PDF price sheet.";
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    uploadStatus.textContent = "This prototype accepts PDFs up to 10 MB.";
    return;
  }
  if (!window.pdfjsLib) {
    uploadStatus.textContent = "The PDF reader is unavailable. Check the internet connection, then try again.";
    return;
  }
  try {
    uploadStatus.textContent = `Reading ${file.name} on this device…`;
    window.pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    const pdf = await window.pdfjsLib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    let text = "";
    for (let pageNumber = 1; pageNumber <= Math.min(pdf.numPages, 3); pageNumber += 1) {
      text += `${textFromPdfPage(await (await pdf.getPage(pageNumber)).getTextContent())}\n`;
    }
    let method = "Searchable PDF text extracted - review required";
    if (text.replace(/\s/g, "").length < 40) {
      method = "Scanned PDF OCR extracted - review required";
      text = await ocrFirstPage(pdf);
    }
    const parsed = parsePriceSheet(text);
    uploadStatus.textContent = `${file.name} was processed on this device. ${parsed.rows.length} possible price row${parsed.rows.length === 1 ? "" : "s"} found.`;
    renderReview(parsed, method, file.name);
  } catch (error) {
    console.error(error);
    uploadStatus.textContent = "The file could not be read automatically. You can choose it again and enter the required fields for review.";
  }
});

document.querySelector("#approve-upload").addEventListener("click", () => {
  if (!currentUpload) return;
  const locality = document.querySelector("#review-locality").value.trim();
  const collectionDate = document.querySelector("#review-date").value;
  const market = document.querySelector("#review-market").value.trim();
  const rows = [...reviewRows.querySelectorAll("tr")].map((row) => ({
    food: row.querySelector('[data-field="food"]').value.trim(),
    unit: row.querySelector('[data-field="unit"]').value.trim(),
    price: parseCop(row.querySelector('[data-field="price"]').value)
  })).filter((row) => row.food || row.unit || row.price);
  const incomplete = !locality || !collectionDate || !rows.length || rows.some((row) => !row.food || !row.unit || !row.price);
  if (incomplete) {
    reviewHelp.textContent = "Please complete locality, collection date, food name, unit, and price for every row before saving.";
    return;
  }
  const now = new Date().toISOString();
  const approved = rows.map((row) => ({ locality, collection_date: collectionDate, market, food: row.food, unit: row.unit, price_cop: row.price, nutrition_status: nutritionStatus(row.food), source_file: currentUpload.filename, extraction_method: currentUpload.method, review_status: "Reviewed locally", saved_at: now }));
  saveRows([...getSavedRows(), ...approved]);
  uploadStatus.textContent = `${approved.length} reviewed observation${approved.length === 1 ? "" : "s"} saved only in this browser.`;
  reviewHelp.textContent = "Saved locally. Price received; nutrition match still needs review for any food without a verified profile.";
  renderSavedSummary();
});

document.querySelector("#download-uploads").addEventListener("click", () => {
  const rows = getSavedRows();
  if (!rows.length) { savedSummary.textContent = "There are no saved observations to download yet."; return; }
  const headings = Object.keys(rows[0]);
  const csv = [headings.join(","), ...rows.map((row) => headings.map((heading) => `"${String(row[heading] ?? "").replace(/"/g, '""')}"`).join(","))].join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = "reviewed_local_price_observations.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});

document.querySelector("#clear-uploads").addEventListener("click", () => {
  localStorage.removeItem(localStorageKey);
  renderSavedSummary();
});

renderSavedSummary();
