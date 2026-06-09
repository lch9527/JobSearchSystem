const STORAGE_KEY = "job-radar.job-actions.v1";
const state = { jobs: [], filtered: [], actions: loadActions() };
const $ = (id) => document.getElementById(id);

const safeText = (value) => String(value ?? "");
const normalized = (value) => safeText(value).toLocaleLowerCase();
const US_LOCATION_PATTERNS = [
  /\bunited states\b/i,
  /\busa\b/i,
  /\bu\.s\.\b/i,
  /\bus\b/i,
  /\bremote[-\s]*(?:us|u\.s\.|united states)\b/i,
  /\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming)\b/i,
  /\b(AK|AL|AR|AZ|CA|CO|CT|DC|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|ME|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA|VT|WA|WI|WV|WY)\b/,
];
const formatDate = (value) => {
  if (!value) return "Unknown date";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
};

function loadActions() {
  try {
    let saved = "{}";
    try {
      saved = localStorage.getItem(STORAGE_KEY) || "{}";
    } catch (storageError) {
      console.warn("Local storage is unavailable", storageError);
    }
    const parsed = JSON.parse(saved || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    console.warn("Could not read saved job actions", error);
    return {};
  }
}

function saveActions() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.actions));
  } catch (error) {
    console.warn("Could not save job actions", error);
  }
}

function jobKey(job) {
  return safeText(job.job_hash) || [job.title, job.company, job.location, job.url].map(safeText).join("||");
}

function legacyJobKey(job) {
  return [job.title, job.company, job.location, job.url].map(safeText).join("||");
}

function migrateActions(actions, jobs) {
  let changed = false;
  for (const job of jobs) {
    const primaryKey = safeText(job.job_hash);
    const fallbackKey = legacyJobKey(job);
    if (!primaryKey || !fallbackKey || primaryKey === fallbackKey) continue;
    if (!actions[primaryKey] && actions[fallbackKey]) {
      actions[primaryKey] = actions[fallbackKey];
      delete actions[fallbackKey];
      changed = true;
    }
  }
  if (changed) {
    saveActions();
  }
  return actions;
}

function populateSelect(id, values) {
  const select = $(id);
  [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b)).forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  });
}

function isUSLocation(location) {
  const text = normalized(location);
  return US_LOCATION_PATTERNS.some((pattern) => pattern.test(text));
}

function setSummary(payload) {
  const jobs = payload.jobs || [];
  $("hero-count").textContent = jobs.length;
  $("strong-count").textContent = jobs.filter((job) => job.match_score >= 70).length;
  $("company-count").textContent = new Set(jobs.map((job) => job.company).filter(Boolean)).size;
  $("remote-count").textContent = jobs.filter((job) => normalized(job.location).includes("remote")).length;
  $("top-score").textContent = Math.max(0, ...jobs.map((job) => job.match_score));
  $("updated-time").textContent = `Updated ${formatDate(payload.generated_at)}`;
}

function setBucketCounts() {
  $("review-count").textContent = state.filtered.review.length;
  $("applyed-count").textContent = state.filtered.applyed.length;
  $("not-fit-count").textContent = state.filtered.notFit.length;
}

function createButton(label, action, jobKeyValue, className = "action-button") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.dataset.action = action;
  button.dataset.jobKey = jobKeyValue;
  button.textContent = label;
  return button;
}

function createJobCard(job, bucket) {
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
  [job.company, job.location || "Location not listed", job.employment_type, `Found ${formatDate(job.date_found)}`]
    .filter(Boolean)
    .forEach((text) => {
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

  const actions = document.createElement("div");
  actions.className = "job-actions";

  const link = document.createElement("a");
  link.className = "apply";
  const target = new URL(job.url, window.location.href);
  link.href = ["http:", "https:"].includes(target.protocol) ? target.href : "#";
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "View job";
  actions.append(link);

  const key = jobKey(job);
  if (bucket === "review") {
    actions.append(
      createButton("applyed", "applyed", key),
      createButton("not fit", "not-fit", key, "action-button secondary")
    );
  } else {
    actions.append(createButton("Move to review", "review", key, "action-button secondary"));
  }

  article.append(score, body, actions);
  return article;
}

function applyFilters() {
  const query = normalized($("search").value.trim());
  const company = $("company-filter").value;
  const status = $("status-filter").value;
  const minimumScore = Number($("score-filter").value);
  const sort = $("sort").value;
  const location = $("location-filter").value;

  const filtered = state.jobs.filter((job) => {
    const haystack = normalized([job.title, job.company, job.location, job.match_reason, job.employment_type].join(" "));
    return (
      (!query || haystack.includes(query)) &&
      (!company || job.company === company) &&
      (!status || job.status === status) &&
      (!location || (location === "us" && isUSLocation(job.location))) &&
      job.match_score >= minimumScore
    );
  });

  filtered.sort((a, b) => {
    if (sort === "newest") return safeText(b.date_found).localeCompare(safeText(a.date_found));
    if (sort === "company") return safeText(a.company).localeCompare(safeText(b.company));
    if (sort === "title") return safeText(a.title).localeCompare(safeText(b.title));
    return b.match_score - a.match_score || safeText(b.date_found).localeCompare(safeText(a.date_found));
  });

  state.filtered = partitionFilteredJobs(filtered);
  render();
}

function partitionFilteredJobs(filteredJobs) {
  const buckets = { review: [], applyed: [], notFit: [] };
  for (const job of filteredJobs) {
    const key = jobKey(job);
    const action = state.actions[key];
    if (action === "applyed") {
      buckets.applyed.push(job);
    } else if (action === "not-fit") {
      buckets.notFit.push(job);
    } else {
      buckets.review.push(job);
    }
  }
  return buckets;
}

function renderSection(containerId, jobs, bucket) {
  const container = $(containerId);
  container.replaceChildren(...jobs.map((job) => createJobCard(job, bucket)));
}

function render() {
  renderSection("job-list", state.filtered.review, "review");
  renderSection("applyed-list", state.filtered.applyed, "applyed");
  renderSection("not-fit-list", state.filtered.notFit, "not-fit");
  $("result-count").textContent = `${state.filtered.review.length} ${state.filtered.review.length === 1 ? "role" : "roles"} in review`;
  setBucketCounts();
}

function resetFilters() {
  $("search").value = "";
  $("company-filter").value = "";
  $("status-filter").value = "";
  $("score-filter").value = "35";
  $("sort").value = "score";
  $("location-filter").value = "";
  applyFilters();
}

function moveJob(jobKeyValue, action) {
  if (action === "review") {
    delete state.actions[jobKeyValue];
  } else {
    state.actions[jobKeyValue] = action;
  }
  saveActions();
  applyFilters();
}

async function start() {
  try {
    const response = await fetch("jobs.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.jobs = payload.jobs || [];
    state.actions = migrateActions(state.actions, state.jobs);
    populateSelect("company-filter", state.jobs.map((job) => job.company));
    populateSelect("status-filter", state.jobs.map((job) => job.status));
    setSummary(payload);
    applyFilters();
  } catch (error) {
    $("result-count").textContent = "Could not load job results";
    console.error(error);
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action][data-job-key]");
  if (!button) return;
  moveJob(button.dataset.jobKey, button.dataset.action);
});

["search", "company-filter", "status-filter", "score-filter", "sort", "location-filter"].forEach((id) => {
  $(id).addEventListener(id === "search" ? "input" : "change", applyFilters);
});
$("clear-filters").addEventListener("click", resetFilters);
start();
