---
title: 'pydapter Developer Style Guide'
by:     'pydapter Team'
created: '2025-05-03'
updated: '2025-05-03'
version: '1.0'
description: >
  Practical coding standards for pydapter.
---

## 1 · Why another guide?

Because **consistency beats cleverness.** If everyone writes code, commits, and
PRs the same way, we spend brain-cycles on the product - not on deciphering each
other's styles.

---

## 2 · What matters (and what doesn't)

| ✅ KEEP                                          | ❌ Let go                      |
| ------------------------------------------------ | ------------------------------ |
| Readability & small functions                    | “One-liner wizardry”           |
| **>80 pct test coverage**                        | 100 pct coverage perfectionism |
| Conventional Commits                             | Exotic git workflows           |
| Search-driven dev (cite results)                 | Coding from memory             |
| Local CLI (`pydapter *`, `git`, `pnpm`, `cargo`) | Heavy bespoke shell wrappers   |
| Tauri security basics                            | Premature micro-optimisation   |

---

## 4 · Golden-path workflow

1. **Research** - `mcp info_group` → paste IDs/links in docs, use the parameters
   thoughtfully.
2. **Spec** - write out spec using template (architect)
3. **Plan + Tests** - write out plan and tests using template (implementer)
4. **Code + Green tests** - actually implement according to plan, local
   `pnpm test`, `cargo test`, `uv run pytest tests`...etc. retain from taking
   the path of least resistance and focus on implmenting the project as per the
   plan. (implementer)
5. **Commit** - use `git` cli
6. **PR** - use `git` cli
7. **CI** - (coverage & template lint)
8. **Review** - reviewer checks search citations + tests, then approves.
9. **Merge & clean** - orchestrator merges; implementer clean up the branch and
   checkout main.

That's it - nine steps, every time.

---

## 5 · Git & commit etiquette

- One logical change per commit.
- Conventional Commit format (`<type>(scope): subject`).
- Example:

feat(ui): add dark-mode toggle

Implements switch component & persists pref in localStorage (search: exa-xyz123

- looked up prefers-color-scheme pattern) Closes #42

---

## 6 · Search-first rule (the only non-negotiable)

If you introduce a new idea, lib, algorithm, or pattern **you must cite at least
one search result ID** (exa-… or pplx-…) in the spec / plan / commit / PR. Tests
& scanners look for that pattern; missing ⇒ reviewer blocks PR.

---

## 7 · FAQ

- **Why isn't X automated?** - Because simpler is faster. We automate only what
  pays its rent in saved time.
- **Can I skip the templates?** - No. They make hand-offs predictable.
- **What if coverage is <80 pct?** - Add tests or talk to the architect to slice
  scope.
- **My search turned up nothing useful.** - Then **cite that**
  (`search:exa - none - no relevant hits`) so the reviewer knows you looked.

Happy hacking 🐝
