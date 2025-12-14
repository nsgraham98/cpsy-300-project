// js/charts.js
let barChart = null;
let scatterChart = null;
let pieChart = null;

export function renderCharts(rawData, filteredAvg) {
  if (!rawData) return;

  const avgLabels = filteredAvg.map((row) => row.Diet_type);
  const proteinData = filteredAvg.map((row) => row["Protein(g)"] || 0);
  const carbsData = filteredAvg.map((row) => row["Carbs(g)"] || 0);
  const fatData = filteredAvg.map((row) => row["Fat(g)"] || 0);

  // BAR CHART
  const barCtx = document.getElementById("barChart").getContext("2d");
  if (barChart) barChart.destroy();
  barChart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels: avgLabels,
      datasets: [
        { label: "Protein (g)", data: proteinData },
        { label: "Carbs (g)", data: carbsData },
        { label: "Fat (g)", data: fatData },
      ],
    },
    options: {
      responsive: true,
      scales: { y: { beginAtZero: true } },
    },
  });

  // SCATTER
  const scatterCtx = document.getElementById("scatterPlot").getContext("2d");
  if (scatterChart) scatterChart.destroy();

  const scatterData = (rawData.top_protein || []).map((row) => ({
    x: row["Carbs(g)"] || 0,
    y: row["Protein(g)"] || 0,
    label: row.Recipe_name || "Recipe",
    diet: row.Diet_type || "Unknown",
  }));

  scatterChart = new Chart(scatterCtx, {
    type: "scatter",
    data: { datasets: [{ label: "Top Protein Recipes", data: scatterData }] },
    options: {
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = ctx.raw;
              return `${p.label} (${p.diet}): Protein ${p.y}g`;
            },
          },
        },
      },
      scales: {
        x: { title: { display: true, text: "Carbs (g)" } },
        y: { title: { display: true, text: "Protein (g)" } },
      },
    },
  });

  // PIE
  const pieCtx = document.getElementById("pieChart").getContext("2d");
  if (pieChart) pieChart.destroy();

  const counts = {};
  (rawData.top_protein || []).forEach((r) => {
    counts[r.Diet_type || "Unknown"] =
      (counts[r.Diet_type || "Unknown"] || 0) + 1;
  });

  pieChart = new Chart(pieCtx, {
    type: "pie",
    data: {
      labels: Object.keys(counts),
      datasets: [{ data: Object.values(counts) }],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });
}
