import json
import tempfile
import unittest
from pathlib import Path

from scripts import discover


def make_repo(**overrides):
    repo = {
        "name": "useful-tool",
        "description": "A useful developer tool for automating local tasks.",
        "fork": False,
        "archived": False,
        "disabled": False,
        "size": 20,
        "stargazers_count": 2,
        "forks_count": 0,
        "pushed_at": "2026-09-20T12:00:00Z",
        "updated_at": "2026-09-20T12:00:00Z",
        "language": "Python",
        "topics": ["developer-tools"],
        "html_url": "https://github.com/example/useful-tool",
        "owner": {
            "login": "example",
            "type": "User",
            "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
            "html_url": "https://github.com/example",
        },
    }
    repo.update(overrides)
    return repo


def normalized_repo(category):
    return discover.normalize(make_repo(), category)


class DiscoveryTests(unittest.TestCase):
    def test_short_terms_do_not_match_inside_other_words(self):
        self.assertTrue(discover.contains_term("VR project", "vr"))
        self.assertFalse(discover.contains_term("VRAM disk", "vr"))
        self.assertTrue(discover.contains_term("REST API", "api"))
        self.assertFalse(discover.contains_term("capital", "api"))

    def test_risky_repository_requires_review(self):
        repo = make_repo(description="A private server and API emulator project")
        self.assertTrue(discover.looks_low_quality(repo))

        download_bait = make_repo(
            description="Get the full version with a free download for Windows."
        )
        self.assertTrue(discover.looks_low_quality(download_bait))

    def test_irrelevant_result_is_not_selected(self):
        repo = make_repo(
            name="VRAMDISK",
            description="Mount graphics memory as a Windows drive for storage.",
            topics=["storage"],
        )
        self.assertEqual(discover.relevance_score(repo, ["vr"]), 0)

    def test_relevant_result_scores(self):
        repo = make_repo(
            name="quest-gallery",
            description="A virtual reality gallery for Meta Quest.",
            topics=["openxr"],
        )
        terms = ["vr", "virtual reality", "meta quest", "openxr"]
        self.assertGreaterEqual(
            discover.relevance_score(repo, terms),
            discover.MIN_CATEGORY_SCORE,
        )

    def test_language_is_valid_category_evidence(self):
        repo = make_repo(
            name="small-project",
            description="A useful command-line utility for local workflows.",
            language="Python",
            topics=[],
        )
        self.assertGreaterEqual(
            discover.relevance_score(repo, ["python"], ["Python"]),
            discover.MIN_CATEGORY_SCORE,
        )

    def test_validation_rejects_partial_results(self):
        with self.assertRaisesRegex(RuntimeError, "no results"):
            discover.validate_results([normalized_repo("Tools")])

    def test_validation_accepts_complete_unique_results(self):
        repos = []

        for index, category in enumerate(discover.CATEGORIES):
            repo = normalized_repo(category)
            repo["repo_url"] = f"https://github.com/example/repo-{index}"
            repos.append(repo)

        discover.validate_results(repos)

    def test_write_results_is_valid_json(self):
        repos = [normalized_repo("Tools")]

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "developers.json"
            discover.write_results(repos, output)
            written = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(written, repos)


if __name__ == "__main__":
    unittest.main()
