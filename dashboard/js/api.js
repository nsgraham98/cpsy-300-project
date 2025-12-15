// js/api.js
//
// Backend is deployed separately as an Azure Function App.
// Local dev  → http://localhost:7071/api
// Production → injected via window.__API_BASE__ (set in index.html at deploy time)
//
// Optional override (dev convenience):
// - localStorage API_BASE_OVERRIDE

const isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

const LS_KEY = "API_BASE_OVERRIDE";

function normalizeBase(base) {
  return String(base || "").replace(/\/+$/, "");
}

function resolveApiBase() {
  // 1) dev override
  const override = localStorage.getItem(LS_KEY);
  if (override) return normalizeBase(override);

  // 2) local dev
  if (isLocal) {
    // If you're running via SWA CLI (default port 4280), use its proxy:
    if (window.location.port === "4280") return "/api";

    // If you're hitting the site from some other dev server, hit Functions directly:
    return "http://localhost:7071/api";
  }

  // 3) production injected
  const injected = window.__API_BASE__;
  if (injected && injected !== "__API_BASE__") return normalizeBase(injected);

  // 4) fail loudly
  throw new Error(
    "API base not configured. window.__API_BASE__ was not injected. " +
      "Check your GitHub Actions 'Inject API base' step and PROD_API_BASE secret."
  );
}

export const API_BASE = resolveApiBase();

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
  const url = new URL(RECIPES_URL, window.location.origin);

  const dietNorm = (diet || "all").trim();
  const qNorm = (q || "").trim();

  if (dietNorm && dietNorm !== "all") url.searchParams.set("diet", dietNorm);
  if (qNorm) url.searchParams.set("q", qNorm);

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
