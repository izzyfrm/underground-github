const repoGrid = document.querySelector("#repoGrid");
const searchInput = document.querySelector("#searchInput");
const categoryFilters = document.querySelector("#categoryFilters");
const sortSelect = document.querySelector("#sortSelect");
const emptyState = document.querySelector("#emptyState");
const resultsStatus = document.querySelector("#resultsStatus");

const repoCount = document.querySelector("#repoCount");
const developerCount = document.querySelector("#developerCount");
const categoryCount = document.querySelector("#categoryCount");

let repos = [];
let currentCategory = "All";

function textValue(value, fallback = "") {
  return typeof value === "string" && value.trim()
    ? value.trim()
    : fallback;
}

function starCount(value) {
  const stars = Number(value);

  return Number.isFinite(stars) && stars >= 0
    ? Math.floor(stars)
    : 0;
}

function escapeHTML(value = "") {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeGitHubURL(value, allowedHosts, fallback = "https://github.com/") {
  try {
    const url = new URL(String(value));

    if (
      url.protocol !== "https:" ||
      !allowedHosts.includes(url.hostname) ||
      url.username ||
      url.password ||
      (url.port && url.port !== "443")
    ) {
      return fallback;
    }

    return url.href;
  } catch {
    return fallback;
  }
}

function normalizeRepo(repo) {
  if (!repo || typeof repo !== "object" || Array.isArray(repo)) {
    return null;
  }

  const username = textValue(repo.username);
  const name = textValue(repo.name);
  const category = textValue(repo.category);

  if (!username || !name || !category) {
    return null;
  }

  return {
    developer: textValue(repo.developer, username),
    username,
    avatar: textValue(repo.avatar),
    name,
    description: textValue(repo.description, "No description provided."),
    category,
    language: textValue(repo.language, "Unknown"),
    stars: starCount(repo.stars),
    topics: Array.isArray(repo.topics)
      ? repo.topics.filter(topic => typeof topic === "string").slice(0, 4)
      : [],
    featured: repo.featured === true,
    profile_url: textValue(repo.profile_url),
    repo_url: textValue(repo.repo_url)
  };
}

function repoCard(repo) {
  const avatarFallback =
    `https://github.com/identicons/${encodeURIComponent(repo.username)}.png`;
  const avatarURL = safeGitHubURL(
    repo.avatar,
    ["avatars.githubusercontent.com"],
    avatarFallback
  );
  const profileURL = safeGitHubURL(repo.profile_url, ["github.com"]);
  const repositoryURL = safeGitHubURL(repo.repo_url, ["github.com"]);
  const topics = repo.topics
    .map(topic => `<span class="tag">${escapeHTML(topic)}</span>`)
    .join("");

  return `
    <article class="repo-card">
      <div class="repo-top">
        <div class="developer">
          <img
            class="avatar"
            src="${escapeHTML(avatarURL)}"
            alt="${escapeHTML(repo.developer)} avatar"
            loading="lazy"
          >

          <div class="developer-text">
            <span class="developer-name">${escapeHTML(repo.developer)}</span>
            <span class="developer-handle">@${escapeHTML(repo.username)}</span>
          </div>
        </div>

        <span class="star-count" aria-label="${repo.stars} ${repo.stars === 1 ? "star" : "stars"}">★ ${repo.stars}</span>
      </div>

      <h3 class="repo-name">${escapeHTML(repo.name)}</h3>

      <p class="repo-description">
        ${escapeHTML(repo.description)}
      </p>

      <div class="tags">
        ${topics}
      </div>

      <div class="repo-footer">
        <span class="repo-meta">
          ${escapeHTML(repo.language)} · underground pick
        </span>

        <div class="repo-links">
          <a
            href="${escapeHTML(profileURL)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Profile
          </a>

          <a
            href="${escapeHTML(repositoryURL)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Repository ↗
          </a>
        </div>
      </div>
    </article>
  `;
}

function renderCategories() {
  const categories = [
    "All",
    ...new Set(repos.map(repo => repo.category).filter(Boolean))
  ];

  categories.splice(
    1,
    categories.length - 1,
    ...categories.slice(1).sort((a, b) => a.localeCompare(b))
  );

  categoryFilters.innerHTML = categories
    .map(category => `
      <button
        class="filter ${category === currentCategory ? "active" : ""}"
        data-category="${escapeHTML(category)}"
        type="button"
      >
        ${escapeHTML(category)}
      </button>
    `)
    .join("");

  categoryCount.textContent = Math.max(categories.length - 1, 0);
}

function getFilteredRepos() {
  const query = searchInput.value.trim().toLowerCase();

  let filtered = repos.filter(repo => {
    const matchesCategory =
      currentCategory === "All" || repo.category === currentCategory;

    const searchable = [
      repo.developer,
      repo.username,
      repo.name,
      repo.description,
      repo.language,
      repo.category,
      ...(repo.topics || [])
    ]
      .join(" ")
      .toLowerCase();

    return matchesCategory && searchable.includes(query);
  });

  switch (sortSelect.value) {
    case "stars-low":
      filtered.sort((a, b) => starCount(a.stars) - starCount(b.stars));
      break;

    case "stars-high":
      filtered.sort((a, b) => starCount(b.stars) - starCount(a.stars));
      break;

    case "name":
      filtered.sort((a, b) => a.name.localeCompare(b.name));
      break;

    default:
      filtered.sort((a, b) => {
        if (Boolean(a.featured) !== Boolean(b.featured)) {
          return Number(b.featured) - Number(a.featured);
        }

        return a.name.localeCompare(b.name);
      });

      break;
  }

  return filtered;
}

function renderRepos() {
  const filtered = getFilteredRepos();

  repoGrid.innerHTML = filtered.map(repoCard).join("");
  repoGrid.setAttribute("aria-busy", "false");
  emptyState.hidden = filtered.length !== 0;

  const noun = filtered.length === 1 ? "project" : "projects";
  resultsStatus.textContent =
    `Showing ${filtered.length} of ${repos.length} ${noun}`;
}

function updateStats() {
  repoCount.textContent = repos.length;

  const developers = new Set(
    repos.map(repo => repo.username).filter(Boolean)
  );

  developerCount.textContent = developers.size;
}

categoryFilters.addEventListener("click", event => {
  const button = event.target.closest("[data-category]");

  if (!button) {
    return;
  }

  currentCategory = button.dataset.category;

  renderCategories();
  renderRepos();
});

searchInput.addEventListener("input", renderRepos);
sortSelect.addEventListener("change", renderRepos);

async function loadRepos() {
  try {
    const response = await fetch("data/developers.json");

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();

    if (!Array.isArray(payload)) {
      throw new TypeError("Repository data must be an array");
    }

    repos = payload.map(normalizeRepo).filter(Boolean);

    if (repos.length === 0) {
      throw new Error("Repository data is empty");
    }

    updateStats();
    renderCategories();
    renderRepos();
  } catch (error) {
    console.error("Could not load repository data:", error);

    repos = [];
    repoGrid.replaceChildren();
    repoGrid.setAttribute("aria-busy", "false");
    categoryFilters.replaceChildren();
    updateStats();
    categoryCount.textContent = "0";
    resultsStatus.textContent = "Project data is unavailable.";

    emptyState.hidden = false;

    emptyState.querySelector("h3").textContent =
      "Could not load repo data";

    emptyState.querySelector("p").textContent =
      "Check data/developers.json and try again.";
  }
}

loadRepos();
