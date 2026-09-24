# Underground GitHub

Underground GitHub is a public directory for discovering active, lesser-known
developers and repositories. The live site is available at
[izzyfrm.github.io/underground-github](https://izzyfrm.github.io/underground-github/).

## How it works

- `scripts/discover.py` searches the GitHub API for recently active public
  repositories with 25 stars or fewer.
- Results must pass quality, category-relevance, URL, duplication, and safety
  checks.
- The scheduled workflow opens or updates a pull request. It does **not**
  publish results directly.
- A person reviews the proposed repositories before merging them into the
  directory served by GitHub Pages.

This process intentionally favors safety and relevance over listing every
possible project. Inclusion is not an endorsement of a repository's code.

## Local checks

The project uses only browser JavaScript and Python's standard library.

```bash
python -m unittest discover -s tests -v
python scripts/discover.py --validate-only
node --check app.js
```

Serve the repository root with any local HTTP server to test the site. Opening
`index.html` directly will not reliably load `data/developers.json` because of
browser file-origin restrictions.

## Submit a repository

Use the [repository submission form](https://github.com/izzyfrm/underground-github/issues/new?template=repo-submission.yml).
Submissions must be public, actively maintained, relevant to one of the listed
categories, and safe for visitors to inspect.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report
security concerns using the instructions in [SECURITY.md](SECURITY.md), not a
public issue.

## License

No license has been selected yet. Until the owner adds one, normal copyright
rules apply. Contributions should not add a license without the owner's
explicit approval.
