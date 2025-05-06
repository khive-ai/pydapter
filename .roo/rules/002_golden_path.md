---
title: "pydapter Golden Path"
by: "Ocean"
scope: "project"
created: "2025-05-05"
updated: "2025-05-05"
version: "1.0"
description: consistent development workflow for pydapter
---

AWLAYS CHECK YOUR BRANCH AND ISSUE, AND KNOW WHAT YOU ARE WORKING ON

## 1 · Why another guide?

Because **consistency beats cleverness.** If everyone writes code, commits, and
PRs the same way, we spend brain-cycles on the product - not on deciphering each
other's styles.

---

## 2 · What matters (and what doesn't)

| ✅ KEEP                                                  | ❌ Let go                      |
| -------------------------------------------------------- | ------------------------------ |
| Readability & small functions                            | “One-liner wizardry”           |
| **>80 pct test coverage**                                | 100 pct coverage perfectionism |
| Conventional Commits                                     | Exotic git workflows           |
| Search-driven dev (cite results)                         | Coding from memory             |
| Local CLI (`git`, `pnpm`, `cargo`, `gh`, `docker`, `uv`) | Heavy bespoke shell wrappers   |
| Tauri security basics                                    | Premature micro-optimisation   |

---

## 3 · Golden-path workflow

1. **Research** (researcher): must use `mcp: info_group` to search for
   information, and cite the search results in the report. Write the research
   report using template `RR_template`, and put under `reports/rr/RR-<issue>.md`
   You are provided with:
   - `exa_search` is good for searches, essentially a search engine
   - `perplexity_search` helps digest the results, and generally is preferred
     for direct specific answers, like `how to do X`,
     `Best practices for Y in 2030`..

2. **Spec** (architect): must read the research report, and write out technical
   design spec using template `TDS_template`, and put under
   `reports/tds/TDS-<issue>.md`.

3. **Plan + Tests** (implementer): write out implementation plan `IP_template`,
   put under `reports/ip/IP-<issue>.md`. Optionally: apply Test driven
   development, using `TI_template`, put test implementation report under
   `reports/ti/TI-<issue>.md`.

4. **Code + Green tests** (implementer): actually implement according to plan,
   retain from taking the path of least resistance and focus on implmenting the
   project as per the plan. Local commands like `pnpm test`, `cargo test`,
   `uv run pytest tests` need to be passed.

5. **Commit** (implementer): `uv run pre-commit run --all-files`, then, use
   `git`, `gh` cli

6. **PR/CI** (implementer): use `git`, `gh` cli, checks need to pass. If not,
   fix locally and push again.

7. **Review** (reviewer): reviewer checks search citations + tests, then write
   review using `QA_template`, put under `reports/qa/QA-<issue>.md`, or if more
   formality is needed, use `CRR_template`, and put under
   `reports/crr/CRR-<issue>.md`. Then need to give opinion on the PR, is it a
   go? leave a comment in the pr. Do not **approve** the PR (same gh account,
   won't work), only comment. then `uv run pre-commit run --all-files` push your
   CRR or QA report to the same branch.

8. **Documentation** (documenter): update relevant documentation,
   `uv run pre-commit run --all-files`, push to same branch

9. **Merge & clean** - orchestrator merges; implementer clean up the branch and
   checkout main.

That's it - nine steps, every time.

## 4. Best Practices

- check which local branch you are working at and which one you **SHOULD** be
  working on
- use command line to manipulate local working branch (refer to
  `100_gh_cli_guide.md`)
- use `uv` to manage virtual environments and dependencies (refer to
  `101_uv_cli_guide.md`)
- must clear commit trees among handoffs.
- if already working on a PR or issue: you can commit to the same branch if
  appropriate, or you can add a patch branch to that particular branch. You need
  to merge the patch branch to the "feature" branch before merging to the main
  branch.
- always checkout the branch to read files locally if you can, since sometimes
  Github MCP tool gives base64 response.
- Follow Conventional Commits.
- Run various cli commands (fmt, test...etc) locally before pushing.
- Keep templates up to date; replace all `{{PLACEHOLDER:…}}`.
- Security, performance, and readability are non-negotiable.
- Be kind - leave code better than you found it. 🚀

## 5. Tricks and Tips

### 5.1 cli usage caveats

when using command line, pay attention to the directory you are in, for example
if you have already done

```
cd frontend
npm install
```

and now you want to build the frontend, the correct command is `npm run build`,
and the wrong answer is `cd frontend && npm run build`.

### 5.2 Citation

- All information from external searches must be properly cited
- Use `...` format for citations
- Cite specific claims rather than general knowledge
- Provide sufficient context around citations
- Never reproduce copyrighted content in entirety, Limit direct quotes to less
  than 25 words
- Do not reproduce song lyrics under any circumstances
- Summarize content in own words when possible

### 5.3 MCP usages

corrcect:

```
{json stuff}
```

---

incorrect:

```
{json stuff}
</use_mcp_tool>
```

### 5.4 Git & commit etiquette

- One logical change per commit.
- Conventional Commit format (`<type>(scope): subject`).
- Example:

```
feat(ui): add dark-mode toggle

Implements switch component & persists pref in localStorage (search: exa-xyz123 - looked up prefers-color-scheme pattern)

Closes #42
```

## 6 · Search-first rule (the only non-negotiable)

If you introduce a new idea, lib, algorithm, or pattern **you must cite at least
one search result ID** (exa-… or pplx-…) in the spec / plan / commit / PR. Tests
& scanners look for that pattern; missing ⇒ reviewer blocks PR.

## 7 · FAQ

- **Why isn't X automated?** - Because simpler is faster. We automate only what
  pays its rent in saved time.
- **Can I skip the templates?** - No. They make hand-offs predictable.
- **What if coverage is <80 pct?** - Add tests or talk to the architect to slice
  scope.
- **My search turned up nothing useful.** - Then **cite that**
  (`search:exa - none - no relevant hits`) so the reviewer knows you looked.

Happy hacking 🐝
