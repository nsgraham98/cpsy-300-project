// js/api.js

// ---------------------------------------------
// API base resolution
// ---------------------------------------------
// Local dev  → http://localhost:7071/api
// Production → https://<your-func-app>.azurewebsites.net/api
//
// You can override by setting window.__API_BASE__
// (easy to inject later if needed)

const isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

export const API_BASE =
  window.__API_BASE__ ||
  (isLocal
    ? "http://localhost:7071/api"
    : "https://diet-analysis-func.azurewebsites.net/api");

// ---------------------------------------------
// Analysis API
// ---------------------------------------------
export const ANALYSIS_URL = `${API_BASE}/diet-analysis`;

export async function fetchAnalysisData() {
  const res = await fetch(ANALYSIS_URL);

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch analysis data (${res.status}): ${text}`);
  }

  return res.json();
}

// ---------------------------------------------
// Recipes API (OFFSET / LIMIT paging)
// ---------------------------------------------
export const RECIPES_URL = `${API_BASE}/recipes`;

export async function fetchRecipes({
  diet = "all",
  q = "",
  pageSize = 12,
  page = 1,
} = {}) {
  const url = new URL(RECIPES_URL);

  // Normalize filters
  const dietNorm = (diet || "all").trim();
  const qNorm = (q || "").trim();

  if (dietNorm && dietNorm !== "all") {
    url.searchParams.set("diet", dietNorm);
  }

  if (qNorm) {
    url.searchParams.set("q", qNorm);
  }

  // Pagination (OFFSET / LIMIT)
  url.searchParams.set("pageSize", String(pageSize));
  url.searchParams.set("page", String(Math.max(1, Number(page) || 1)));

  const res = await fetch(url.toString());
  const text = await res.text();

  if (!res.ok) {
    throw new Error(`Failed to fetch recipes (${res.status}): ${text}`);
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Unexpected response from recipes API: ${text}`);
  }
}
