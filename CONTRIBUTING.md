# Contributing

Thanks for helping improve Underground GitHub.

## Repository submissions

Use the repository submission issue form rather than editing
`data/developers.json` directly. A submission should:

- link to a public GitHub repository;
- be actively maintained and have 25 stars or fewer;
- clearly fit one of the directory categories;
- contain a meaningful description and enough source code to evaluate; and
- not distribute malware, credential theft, pirated material, access bypasses,
  or other content that creates an unreasonable risk for visitors.

## Code changes

1. Keep the site dependency-free unless a dependency has a clear benefit.
2. Run `python -m unittest discover -s tests -v`.
3. Run `node --check app.js`.
4. Explain user-visible behavior and testing in the pull request.

Automated discovery changes must remain review-only. Do not restore direct
scheduled commits to `main`.
