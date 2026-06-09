const state = { jobs: [], filtered: [] };
const $ = (id) => document.getElementById(id);

const safeText = (value) => String(value ?? "");
const normalized = (value) => safeText(value).toLocaleLowerCase();
const formatDate = (value) => {
  if (!value) return "Unknown date";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
};

function populateSelect(id, values) {
  const select = $(id);
  [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b)).forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  });
}

function setSummary(payload) {
  const jobs = payload.jobs;
  $("hero-count").textContent = jobs.length;
  $("strong-count").textContent = jobs.filter((job) => job.match_score >= 70).length;
  $("company-count").textContent = new Set(jobs.map((job) => job.company).filter(Boolean)).size;
  $("remote-count").textContent = jobs.filter((job) => normalized(job.location).includes("remote")).length;
  $("top-score").textContent = Math.max(0, ...jobs.map((job) => job.match_score));
  $("updated-time").textContent = `Updated ${formatDate(payload.generated_at)}`;
}

function createJobCard(job) {
  const article = document.createElement("article");
  article.className = "job-card";

  const score = document.createElement("div");
  score.className = `score ${job.match_score >= 70 ? "high" : ""}`;
  score.textContent = job.match_score;
  score.title = `Match score ${job.match_score} out of 100`;

  const body = document.createElement("div");
  const title = document.createElement("h3");
  title.className = "job-title";
  title.textContent = job.title;

  const meta = document.createElement("div");
  meta.className = "job-meta";
  [job.company, job.location || "Location not listed", job.employment_type, `Found ${formatDate(job.date_found)}`].filter(Boolean).forEach((text) => {
    const span = document.createElement("span");
    span.textContent = text;
    meta.append(span);
  });
  const status = document.createElement("span");
  status.className = "tag";
  status.textContent = job.status || "New";
  meta.append(status);

  const reason = document.createElement("p");
  reason.className = "job-reason";
  reason.textContent = job.match_reason || "Matched configured job criteria.";
  body.append(title, meta, reason);

  const link = document.createElement("a");
  link.className = "apply";
  const target = new URL(job.url, window.location.href);
  link.href = ["http:", "https:"].includes(target.protocol) ? target.href : "#";
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "View job ↗";
  article.append(score, body, link);
  return article;
}

function applyFilters() {
  const query = normalized($("search").value.trim());
  const company = $("company-filter").value;
  const status = $("status-filter").value;
  const minimumScore = Number($("score-filter").value);
  const sort = $("sort").value;

  state.filtered = state.jobs.filter((job) => {
    const haystack = normalized([job.title, job.company, job.location, job.match_reason, job.employment_type].join(" "));
    return (!query || haystack.includes(query)) && (!company || job.company === company) && (!status || job.status === status) && job.match_score >= minimumScore;
  });

  state.filtered.sort((a, b) => {
    if (sort === "newest") return safeText(b.date_found).localeCompare(safeText(a.date_found));
    if (sort === "company") return safeText(a.company).localeCompare(safeText(b.company));
    if (sort === "title") return safeText(a.title).localeCompare(safeText(b.title));
    return b.match_score - a.match_score || safeText(b.date_found).localeCompare(safeText(a.date_found));
  });
  render();
}

function render() {
  const list = $("job-list");
  list.replaceChildren(...state.filtered.map(createJobCard));
  $("result-count").textContent = `${state.filtered.length} ${state.filtered.length === 1 ? "role" : "roles"} on your radar`;
  $("empty-state").hidden = state.filtered.length !== 0;
}

function resetFilters() {
  $("search").value = "";
  $("company-filter").value = "";
  $("status-filter").value = "";
  $("score-filter").value = "35";
  $("sort").value = "score";
  applyFilters();
}

async function start() {
  try {
    const response = await fetch("jobs.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.jobs = payload.jobs || [];
    populateSelect("company-filter", state.jobs.map((job) => job.company));
    populateSelect("status-filter", state.jobs.map((job) => job.status));
    setSummary(payload);
    applyFilters();
  } catch (error) {
    $("result-count").textContent = "Could not load job results";
    $("empty-state").hidden = false;
    $("empty-state").querySelector("p").textContent = "Run the website generator and refresh this page.";
    console.error(error);
  }
}

["search", "company-filter", "status-filter", "score-filter", "sort"].forEach((id) => {
  $(id).addEventListener(id === "search" ? "input" : "change", applyFilters);
});
$("clear-filters").addEventListener("click", resetFilters);
start();
