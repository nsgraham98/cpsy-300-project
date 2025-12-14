// js/api.js
export const FUNCTION_URL = "/api/diet-analysis";

export async function fetchAnalysisData() {
  const res = await fetch(FUNCTION_URL);
  if (!res.ok) {
    throw new Error("Failed to fetch data from Azure Function");
  }
  return res.json();
}

export const RECIPES_URL = "/api/recipes";

export async function fetchRecipes({
  diet = "all",
  q = "",
  pageSize = 12,
  page = 1, // ✅ NEW (numeric page)
  token = null, // ❌ legacy, ignored for OFFSET/LIMIT
} = {}) {
  const url = new URL(RECIPES_URL, window.location.origin);

  // Normalize filters
  const dietNorm = (diet || "all").trim();
  const qNorm = (q || "").trim();

  if (dietNorm && dietNorm !== "all") url.searchParams.set("diet", dietNorm);
  if (qNorm) url.searchParams.set("q", qNorm);

  // Pagination (OFFSET/LIMIT)
  url.searchParams.set("pageSize", String(pageSize));
  url.searchParams.set("page", String(Math.max(1, Number(page) || 1)));

  // IMPORTANT: Do NOT send continuation tokens with OFFSET/LIMIT paging
  // if (token) url.searchParams.set("token", token);

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
