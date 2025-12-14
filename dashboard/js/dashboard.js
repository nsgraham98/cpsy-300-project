// js/dashboard.js
import { fetchAnalysisData, fetchRecipes } from "./api.js";
import { renderCharts } from "./charts.js";
import { resetRecipePaging, loadRecipesPage } from "./recipes.js";
import { initAuth } from "./auth.js";

let rawData = null;

function populateDietFilter(data) {
  const dietFilter = document.getElementById("dietFilter");
  dietFilter.innerHTML = '<option value="all">All Diet Types</option>';

  const diets = new Set();
  (data.avg_macros || []).forEach((r) => r.Diet_type && diets.add(r.Diet_type));

  [...diets].sort().forEach((diet) => {
    const opt = document.createElement("option");
    opt.value = diet;
    opt.textContent = diet;
    dietFilter.appendChild(opt);
  });
}

function getFilteredAvg() {
  if (!rawData) return [];

  const search = document
    .getElementById("searchDietInput")
    .value.trim()
    .toLowerCase();
  const selected = document.getElementById("dietFilter").value;

  return (rawData.avg_macros || []).filter((r) => {
    const diet = (r.Diet_type || "").toLowerCase();
    return (
      (!search || diet.includes(search)) &&
      (selected === "all" || r.Diet_type === selected)
    );
  });
}

async function loadDashboard() {
  rawData = await fetchAnalysisData();

  document.getElementById("last-updated").textContent =
    new Date().toLocaleString();
  document.getElementById("exec-time").textContent =
    (rawData.metadata?.execution_time_ms ?? "--") + " ms";

  populateDietFilter(rawData);
  renderCharts(rawData, getFilteredAvg());
}

function debounce(fn, ms = 250) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function refreshAll() {
  renderCharts(rawData, getFilteredAvg());
  resetRecipePaging();
  await loadRecipesPage(fetchRecipes, "first");
}

document.addEventListener("DOMContentLoaded", () => {
  initAuth({
    onLoggedIn: async () => {
      document
        .getElementById("refreshBtn")
        .addEventListener("click", async () => {
          await loadDashboard();
          await refreshAll();
        });

      // document
      //   .getElementById("getInsightsBtn")
      //   .addEventListener("click", async () => {
      //     await loadDashboard();
      //     await refreshAll();
      //   });

      // Debounced input (prevents hammering charts + API)
      const onSearchInput = debounce(() => {
        refreshAll();
      }, 250);

      document
        .getElementById("searchDietInput")
        .addEventListener("input", onSearchInput);

      document.getElementById("dietFilter").addEventListener("change", () => {
        refreshAll();
      });

      document
        .getElementById("nextBtn")
        .addEventListener("click", () => loadRecipesPage(fetchRecipes, "next"));

      document
        .getElementById("prevBtn")
        .addEventListener("click", () => loadRecipesPage(fetchRecipes, "prev"));

      await loadDashboard();
      resetRecipePaging();
      await loadRecipesPage(fetchRecipes, "first");
    },
  });
});
