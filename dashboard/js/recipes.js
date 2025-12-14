// js/recipes.js

let pageNum = 1;

// Lock the query used for a paging "session" (page 1 -> page N)
// so paging doesn't change mid-stream when the user types/filters.
let activeQuery = { diet: "all", q: "" };

function readQueryFromUI() {
  const diet = (document.getElementById("dietFilter")?.value || "all").trim();
  const q = (document.getElementById("searchDietInput")?.value || "").trim();
  return { diet, q };
}

export function resetRecipePaging() {
  pageNum = 1;
  activeQuery = readQueryFromUI();

  const pageNumEl = document.getElementById("pageNum");
  if (pageNumEl) pageNumEl.textContent = "1";

  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  if (prevBtn) prevBtn.disabled = true;
  if (nextBtn) nextBtn.disabled = true;
}

export async function loadRecipesPage(fetchRecipesFn, direction = "first") {
  // direction: "first" | "next" | "prev"
  const resultsEl = document.getElementById("recipeResults");
  const metaEl = document.getElementById("recipesMeta");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const pageNumEl = document.getElementById("pageNum");

  if (!resultsEl || !metaEl || !prevBtn || !nextBtn || !pageNumEl) return;

  // Determine target page + lock query on "first"
  if (direction === "first") {
    pageNum = 1;
    activeQuery = readQueryFromUI();
  } else if (direction === "next") {
    pageNum += 1;
  } else if (direction === "prev") {
    pageNum = Math.max(1, pageNum - 1);
  }

  resultsEl.innerHTML = `<div class="col-span-full text-center text-gray-600">Loading recipes...</div>`;
  metaEl.textContent = "";

  // Fetch (OFFSET/LIMIT mode: page + pageSize)
  let data;
  try {
    data = await fetchRecipesFn({
      diet: activeQuery.diet,
      q: activeQuery.q,
      pageSize: 12,
      page: pageNum,
      // token intentionally not used
    });
  } catch (err) {
    console.error(err);
    resultsEl.innerHTML = `<div class="col-span-full text-center text-red-600">Failed to load recipes.</div>`;
    metaEl.textContent = "";
    // Roll back page change on failure for nicer UX
    if (direction === "next") pageNum = Math.max(1, pageNum - 1);
    if (direction === "prev") pageNum = pageNum + 1; // we decreased before fetch
    return;
  }

  // Render results
  const items = data.items || [];
  if (items.length === 0) {
    resultsEl.innerHTML = `<div class="col-span-full text-center text-gray-600">No recipes found.</div>`;
  } else {
    resultsEl.innerHTML = items
      .map(
        (r) => `
      <div class="bg-white p-4 shadow rounded-lg">
        <div class="font-semibold mb-1">${escapeHtml(
          r.Recipe_name ?? "Recipe"
        )}</div>
        <div class="text-sm text-gray-600 mb-2">
          ${escapeHtml(r.Diet_type ?? "Unknown Diet")}
          ${r.Cuisine_type ? ` • ${escapeHtml(r.Cuisine_type)}` : ""}
        </div>

        <div class="text-sm grid grid-cols-2 gap-2">
          <div><span class="text-gray-500">Calories:</span> ${fmt(
            r.Calories
          )}</div>
          <div><span class="text-gray-500">Protein:</span> ${fmt(
            r["Protein(g)"]
          )}g</div>
          <div><span class="text-gray-500">Carbs:</span> ${fmt(
            r["Carbs(g)"]
          )}g</div>
          <div><span class="text-gray-500">Fat:</span> ${fmt(
            r["Fat(g)"]
          )}g</div>
        </div>
      </div>
    `
      )
      .join("");
  }

  // Update page label + buttons using backend hints
  pageNumEl.textContent = String(pageNum);

  const hasMore = Boolean(data.hasMore);
  prevBtn.disabled = pageNum <= 1;
  nextBtn.disabled = !hasMore;

  metaEl.textContent = `Showing ${items.length} recipes • Page ${pageNum}`;
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return "--";
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(0) : String(v);
}

// basic XSS-safe escaping for innerHTML
function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
