// js/charts.js
// Refactor: single chart manager + safer transforms + better defaults.

let charts = {
  bar: null,
  scatter: null,
  pie: null,
};

function n(v) {
  const x = Number(v);
  return Number.isFinite(x) ? x : 0;
}

function byDietCounts(rows = []) {
  const counts = new Map();
  for (const r of rows) {
    const diet = (r?.Diet_type || "Unknown").trim() || "Unknown";
    counts.set(diet, (counts.get(diet) || 0) + 1);
  }
  // Sort desc
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function topNDiets(avgRows = [], max = 12) {
  // Keep charts readable by limiting diets shown.
  // Sort by Protein desc (tie-break by name).
  const sorted = [...avgRows].sort((a, b) => {
    const dp = n(b["Protein(g)"]) - n(a["Protein(g)"]);
    if (dp !== 0) return dp;
    return String(a.Diet_type || "").localeCompare(String(b.Diet_type || ""));
  });
  return sorted.slice(0, max);
}

function ensureCtx(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  const ctx = el.getContext("2d");
  return ctx || null;
}

function destroyAll() {
  Object.values(charts).forEach((c) => c && c.destroy());
  charts = { bar: null, scatter: null, pie: null };
}

function buildBar(filteredAvg) {
  const ctx = ensureCtx("barChart");
  if (!ctx) return;

  // Keep it readable when you have many diets
  const rows = topNDiets(filteredAvg, 12);

  const labels = rows.map((r) => r.Diet_type || "Unknown");
  const protein = rows.map((r) => n(r["Protein(g)"]));
  const carbs = rows.map((r) => n(r["Carbs(g)"]));
  const fat = rows.map((r) => n(r["Fat(g)"]));

  if (charts.bar) charts.bar.destroy();

  charts.bar = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Protein (g)", data: protein },
        { label: "Carbs (g)", data: carbs },
        { label: "Fat (g)", data: fat },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            footer: (items) => {
              // Show total macros for the bar
              const p = n(items?.[0]?.parsed?.y);
              const c = n(items?.[1]?.parsed?.y);
              const f = n(items?.[2]?.parsed?.y);
              const total = (p + c + f).toFixed(0);
              return `Total macros: ${total}g`;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 45,
            minRotation: 0,
            autoSkip: true,
          },
        },
        y: { beginAtZero: true, title: { display: true, text: "Grams" } },
      },
    },
  });
}

function buildScatter(rawData) {
  const ctx = ensureCtx("scatterPlot");
  if (!ctx) return;

  const rows = rawData?.top_protein || [];

  // Color palette (cycled if many diets)
  const COLORS = [
    "#2563eb", // blue
    "#16a34a", // green
    "#dc2626", // red
    "#9333ea", // purple
    "#ea580c", // orange
    "#0891b2", // cyan
    "#ca8a04", // amber
    "#4b5563", // gray
  ];

  // Group points by diet
  const byDiet = new Map();

  rows.forEach((r) => {
    const diet = r.Diet_type || "Unknown";

    const point = {
      x: n(r["Carbs(g)"]),
      y: n(r["Protein(g)"]),
      fat: n(r["Fat(g)"]),
      name: r.Recipe_name || "Recipe",
      diet,
    };

    if (!byDiet.has(diet)) byDiet.set(diet, []);
    byDiet.get(diet).push(point);
  });

  const datasets = [...byDiet.entries()].map(([diet, points], i) => {
    const color = COLORS[i % COLORS.length];

    return {
      label: diet,
      data: points,
      backgroundColor: color,
      borderColor: color,
      pointRadius: (ctx) => {
        const fat = n(ctx.raw?.fat);
        return Math.max(3, Math.min(10, 3 + fat / 10));
      },
      pointHoverRadius: 10,
    };
  });

  if (charts.scatter) charts.scatter.destroy();

  charts.scatter = new Chart(ctx, {
    type: "scatter",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            usePointStyle: true,
          },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = ctx.raw;
              return `${p.name} • ${p.diet}`;
            },
            afterLabel: (ctx) => {
              const p = ctx.raw;
              return [
                `Protein: ${p.y.toFixed(0)}g`,
                `Carbs: ${p.x.toFixed(0)}g`,
                `Fat: ${p.fat.toFixed(0)}g`,
              ];
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Carbs (g)" },
          beginAtZero: true,
        },
        y: {
          title: { display: true, text: "Protein (g)" },
          beginAtZero: true,
        },
      },
    },
  });
}

function buildPie(filteredAvg) {
  const ctx = ensureCtx("pieChart");
  if (!ctx) return;

  // Aggregate protein density by diet
  const byDiet = new Map();

  (filteredAvg || []).forEach((r) => {
    const diet = r.Diet_type || "Unknown";
    const p = n(r["Protein(g)"]);
    const c = n(r["Carbs(g)"]);
    const f = n(r["Fat(g)"]);
    const total = p + c + f;

    if (total <= 0) return;

    const density = p / total;

    byDiet.set(diet, (byDiet.get(diet) || 0) + density);
  });

  // Convert to arrays and keep top diets
  const sorted = [...byDiet.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);

  const labels = sorted.map(([diet]) => diet);
  const values = sorted.map(([, val]) => +val.toFixed(3));

  if (charts.pie) charts.pie.destroy();

  charts.pie = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const diet = ctx.label;
              const raw = ctx.raw;
              const sum = values.reduce((a, b) => a + b, 0);
              const pct = sum > 0 ? ((raw / sum) * 100).toFixed(1) : 0;
              return `${diet}: ${pct}% protein density share`;
            },
          },
        },
      },
    },
  });
}

// Public API
export function renderCharts(rawData, filteredAvg) {
  if (!rawData) return;

  // If Chart.js isn't loaded, fail softly
  if (typeof Chart === "undefined") {
    console.warn("Chart.js not found on page.");
    return;
  }

  buildBar(filteredAvg || []);
  buildScatter(rawData);
  buildPie(filteredAvg || []);
}

export function resetCharts() {
  destroyAll();
}
