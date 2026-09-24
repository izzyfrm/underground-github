import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN", "")
OUTPUT = Path("data/developers.json")

MAX_STARS = 25
PER_CATEGORY = 6
ACTIVE_DAYS = 180
SEARCH_PAUSE = 5
MIN_CATEGORY_SCORE = 4

CATEGORIES = {
    "VR": {
        "searches": ["vrchat", '"virtual reality"', "openxr"],
        "terms": [
            "vr",
            "vrchat",
            "virtual reality",
            "meta quest",
            "unity xr",
            "openxr",
        ],
    },
    "Discord": {
        "search": "discord",
        "terms": ["discord", "discord bot", "discord.py", "discord.js"],
    },
    "Python": {
        "search": "python",
        "terms": ["python", "pyqt", "tkinter", "fastapi", "flask"],
        "languages": ["Python"],
    },
    "Web": {
        "search": '"web app"',
        "terms": ["web app", "website", "frontend", "web", "react"],
    },
    "Games": {
        "search": "game",
        "terms": ["game", "pygame", "godot", "unity", "gamedev"],
    },
    "Tools": {
        "search": "cli",
        "terms": ["cli", "tool", "utility", "developer tool", "automation"],
    },
    "APIs": {
        "searches": ["fastapi", '"rest api"', '"public api"'],
        "terms": ["api", "rest api", "fastapi", "backend", "endpoint"],
    },
}

BLOCKED_WORDS = {
    "assignment",
    "homework",
    "tutorial",
    "practice",
    "learning",
    "course",
    "leetcode",
    "hello-world",
    "boilerplate",
    "template",
}

# Repositories matching these terms need human review and must never be added
# automatically. This deliberately favors visitor safety over recall.
REVIEW_REQUIRED_TERMS = {
    "credential stealer",
    "claim a free",
    "download and install",
    "exploit kit",
    "free download",
    "free game key",
    "full version",
    "keylogger",
    "malware",
    "man-in-the-middle",
    "mitm",
    "no storefront required",
    "phishing",
    "pirated",
    "private server",
    "ransomware",
    "remote access trojan",
    "token grabber",
}


def contains_term(value, term):
    """Match a word or phrase without treating substrings as matches."""
    pattern = rf"(?<![\w]){re.escape(term.casefold())}(?![\w])"
    return re.search(pattern, value.casefold()) is not None


def request_json(url, retries=3):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "underground-github",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    for attempt in range(retries):
        request = Request(url, headers=headers)

        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")

            if error.code == 404:
                return None

            retryable = error.code in {403, 429} or 500 <= error.code < 600

            if retryable and attempt < retries - 1:
                retry_after = error.headers.get("Retry-After")

                if retry_after and retry_after.isdigit():
                    wait = int(retry_after)
                else:
                    wait = 20 * (attempt + 1)

                print(
                    f"[rate limit] waiting {wait}s before retry "
                    f"{attempt + 2}/{retries}"
                )
                time.sleep(wait)
                continue

            raise RuntimeError(
                f"GitHub API error {error.code}: {body}"
            ) from error

        except (TimeoutError, URLError, OSError) as error:
            if attempt < retries - 1:
                wait = 10 * (attempt + 1)
                print(
                    f"[network] waiting {wait}s before retry "
                    f"{attempt + 2}/{retries}: {error}"
                )
                time.sleep(wait)
                continue

            raise RuntimeError(
                f"GitHub API request failed after {retries} attempts: {error}"
            ) from error

    return None


def github_search(category, search_term, cutoff):
    query = (
        f"{search_term} in:name,description,readme "
        f"stars:0..{MAX_STARS} "
        f"pushed:>={cutoff} "
        "fork:false archived:false"
    )

    url = (
        f"{API}/search/repositories"
        f"?q={quote(query)}"
        "&sort=updated"
        "&order=desc"
        "&per_page=30"
    )

    data = request_json(url) or {}
    items = data.get("items", [])

    print(f"[{category}] {len(items)} results for {search_term!r}")

    return items


def looks_low_quality(repo):
    name = repo["name"].lower()
    description = (repo.get("description") or "").strip()
    topics = repo.get("topics", [])
    searchable = " ".join([name, description, *topics])

    if repo.get("fork"):
        return True

    if repo.get("archived") or repo.get("disabled"):
        return True

    if repo["owner"].get("type") != "User":
        return True

    if repo.get("stargazers_count", 0) > MAX_STARS:
        return True

    if len(description) < 18:
        return True

    if repo.get("size", 0) < 8:
        return True

    if any(contains_term(name, word) for word in BLOCKED_WORDS):
        return True

    if any(contains_term(searchable, term) for term in REVIEW_REQUIRED_TERMS):
        return True

    return False


def relevance_score(repo, terms, languages=()):
    name = repo["name"].lower()
    description = (repo.get("description") or "").lower()
    topics = [topic.lower() for topic in repo.get("topics", [])]

    score = 0

    for term in terms:
        term = term.lower()

        if contains_term(name, term):
            score += 8

        if contains_term(description, term):
            score += 4

        if any(contains_term(topic, term) for topic in topics):
            score += 5

    language = (repo.get("language") or "").casefold()

    if language in {value.casefold() for value in languages}:
        score += 5

    return score


def match_score(repo, terms, languages=()):
    score = relevance_score(repo, terms, languages)
    stars = repo.get("stargazers_count", 0)

    if 1 <= stars <= 5:
        score += 4
    elif stars <= 12:
        score += 2

    if repo.get("forks_count", 0) > 0:
        score += 1

    pushed = repo.get("pushed_at")

    if pushed:
        pushed_date = datetime.fromisoformat(
            pushed.replace("Z", "+00:00")
        )

        age = datetime.now(timezone.utc) - pushed_date

        if age.days <= 30:
            score += 4
        elif age.days <= 90:
            score += 2

    return score


def normalize(repo, category):
    owner = repo["owner"]["login"]

    return {
        "developer": owner,
        "username": owner,
        "avatar": repo["owner"]["avatar_url"],
        "name": repo["name"],
        "description": repo.get("description") or "",
        "category": category,
        "language": repo.get("language") or "Unknown",
        "stars": repo.get("stargazers_count", 0),
        "topics": repo.get("topics", [])[:4],
        "updated": repo.get("pushed_at") or repo.get("updated_at"),
        "featured": False,
        "profile_url": repo["owner"]["html_url"],
        "repo_url": repo["html_url"],
    }


def discover_category(category, config, cutoff):
    search_terms = config.get("searches", [config.get("search")])
    repos = []
    seen_search_urls = set()

    for search_term in search_terms:
        for repo in github_search(category, search_term, cutoff):
            if repo["html_url"] in seen_search_urls:
                continue

            seen_search_urls.add(repo["html_url"])
            repos.append(repo)

    filtered = []

    for repo in repos:
        if looks_low_quality(repo):
            continue

        score = relevance_score(
            repo,
            config["terms"],
            config.get("languages", ()),
        )

        if score < MIN_CATEGORY_SCORE:
            continue

        filtered.append(repo)

    ranked = sorted(
        filtered,
        key=lambda repo: (
            -match_score(
                repo,
                config["terms"],
                config.get("languages", ()),
            ),
            repo.get("stargazers_count", 0),
            repo["name"].lower(),
        ),
    )

    return [
        normalize(repo, category)
        for repo in ranked[:PER_CATEGORY]
    ]


def mark_featured(repos):
    def updated_timestamp(repo):
        value = repo.get("updated") or ""

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            return 0

    ranked = sorted(
        repos,
        key=lambda repo: (
            repo["stars"],
            -updated_timestamp(repo),
        ),
    )

    featured_urls = {
        repo["repo_url"]
        for repo in ranked[: min(8, len(ranked))]
    }

    for repo in repos:
        repo["featured"] = repo["repo_url"] in featured_urls


def validate_results(repos):
    if not repos:
        raise RuntimeError(
            "No repositories were discovered. Keeping the current data."
        )

    expected_categories = set(CATEGORIES)
    actual_categories = {repo["category"] for repo in repos}
    missing_categories = expected_categories - actual_categories

    if missing_categories:
        missing = ", ".join(sorted(missing_categories))
        raise RuntimeError(
            f"Discovery produced no results for: {missing}. "
            "Keeping the current data."
        )

    repo_urls = [repo["repo_url"] for repo in repos]

    if len(repo_urls) != len(set(repo_urls)):
        raise RuntimeError(
            "Discovery produced duplicate repository URLs. "
            "Keeping the current data."
        )

    for repo in repos:
        if not repo["repo_url"].startswith("https://github.com/"):
            raise RuntimeError("Discovery produced an invalid repository URL.")

        if not repo["profile_url"].startswith("https://github.com/"):
            raise RuntimeError("Discovery produced an invalid profile URL.")

        if not repo["avatar"].startswith(
            "https://avatars.githubusercontent.com/"
        ):
            raise RuntimeError("Discovery produced an invalid avatar URL.")


def write_results(repos, output=OUTPUT):
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")

    temporary.write_text(
        json.dumps(repos, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def main():
    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=ACTIVE_DAYS)
    ).date().isoformat()

    all_repos = []
    seen_urls = set()

    for index, (category, config) in enumerate(CATEGORIES.items()):
        print(f"\n--- {category} ---")

        discovered = discover_category(
            category,
            config,
            cutoff,
        )

        for repo in discovered:
            if repo["repo_url"] in seen_urls:
                continue

            seen_urls.add(repo["repo_url"])
            all_repos.append(repo)

        if index < len(CATEGORIES) - 1:
            print(f"[pause] waiting {SEARCH_PAUSE}s")
            time.sleep(SEARCH_PAUSE)

    mark_featured(all_repos)

    all_repos.sort(
        key=lambda repo: (
            repo["category"].lower(),
            -int(repo["featured"]),
            repo["stars"],
            repo["name"].lower(),
        )
    )

    validate_results(all_repos)
    write_results(all_repos)

    print(
        f"\nSaved {len(all_repos)} repos "
        f"to {OUTPUT}"
    )


if __name__ == "__main__":
    main()
