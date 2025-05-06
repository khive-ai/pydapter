---
title: "Git & GitHub CLI Quick Reference Guide"
by: "Ocean"
scope: "project"
created: "2025-05-05"
updated: "2025-05-05"
version: "1.0"
description: >
    Essential Git and GitHub (`gh`) command-line interface practices and commands
---

# pydapter Team: Git & GitHub CLI Quick Reference Guide

**Core Principle:** Prioritize using `git` and `gh` CLI commands for repository
interactions.

## 1. Initial Setup & Local Environment Checks

- **Check Status & Branch:**
  ```bash
  git status
  git branch
  ```
- **Check Current Directory:**
  ```bash
  pwd
  ```
- **Switch Branch:**
  ```bash
  git checkout <branch_name>
  ```
- **Update Local `main` from Remote:** (Do this often, especially before
  creating new branches)
  ```bash
  git checkout main
  git fetch origin        # Fetch remote changes without merging
  git pull origin main    # Fetch and merge (or rebase if configured) remote main into local main
  # OR (Use with caution - discards local main changes):
  # git reset --hard origin/main
  ```

## 2. Standard Feature Workflow via CLI

1. **Create Feature Branch:** (Ensure `main` is updated first)
   ```bash
   git checkout main
   # git pull origin main # (If needed)
   git checkout -b feature/<issue_id>-brief-description # e.g., feature/150-add-dark-mode
   ```
2. **(Perform Development Work...)**
3. **Local Validation (MANDATORY before commit/push):**
   ```bash
   # Run linters, formatters, tests as defined for the project
   uv run pre-commit run --all-files
   # pnpm test | cargo test | uv run pytest tests | etc.
   ```
4. **Stage Changes:**
   ```bash
   git add <specific_file>... # Stage specific files
   git add .                   # Stage all changes in current dir (use carefully)
   git add -p                  # Interactively stage changes (recommended for review)
   ```
5. **Commit Changes:** (Follow Conventional Commits - See Section 3)
   ```bash
   git commit -m "type(scope): subject" -m "Body explaining what/why. Closes #<issue_id>. search: <id>..."
   # OR use 'git commit' to open editor for longer messages
   ```
6. **Push Branch to Remote:**
   ```bash
   # First time pushing the new branch:
   git push -u origin feature/<issue_id>-brief-description
   # Subsequent pushes:
   git push
   ```
7. **Create Pull Request:**
   ```bash
   gh pr create --title "type(scope): Title (Closes #<issue_id>)" --body "Description..." --base main --head feature/<issue_id>-brief-description
   # OR use interactive mode:
   # gh pr create
   ```
8. **Monitor PR Checks:**
   ```bash
   gh pr checks <pr_number_or_branch_name>
   # Or gh pr status
   ```
9. **Checkout PR Locally (for review/testing):**
   ```bash
   gh pr checkout <pr_number>
   ```
10. **Address Review Feedback:**
    ```bash
    # Make code changes...
    # Run local validation again!
    git add <changed_files>
    git commit -m "fix(scope): address review comment xyz" -m "Detailed explanation..."
    git push
    ```
11. **Cleanup After Merge:** (PR merged by Orchestrator)
    ```bash
    git checkout main
    git pull origin main # Ensure main is updated
    git branch -d feature/<issue_id>-brief-description # Delete local branch
    git push origin --delete feature/<issue_id>-brief-description # Delete remote branch (optional)
    ```

## 3. Committing: Conventional Commits & Hygiene

- **Format:** `<type>(<scope>): <subject>` **(Mandatory)**
  - `<type>`: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`,
    `refactor`, `perf`, `test`.
  - `<scope>`: Optional module/area (e.g., `ui`, `api`).
  - `<subject>`: Imperative mood, brief description.
- **Body:** Use `git commit` (no `-m`) for multi-line messages. Explain _what_
  and _why_. Reference Issues (`Closes #...`) and **cite searches**
  (`search: ...`).
- **Atomicity:** One logical change per commit.
- **Clean History:** Before pushing a branch for PR or handing off, consider
  cleaning up minor fixups using interactive rebase (`git rebase -i main`). Use
  with caution, especially after pushing.

## 4. Branching Strategy via CLI

- **Create:** `git checkout -b <branch_name>` (usually from `main`).
- **Switch:** `git checkout <branch_name>`.
- **List:** `git branch` (local), `git branch -r` (remote), `git branch -a`
  (all).
- **Delete Local:** `git branch -d <branch_name>` (safe),
  `git branch -D <branch_name>` (force).
- **Delete Remote:** `git push origin --delete <branch_name>`.
- **Patch Branches:** If needed for complex fixes on an existing feature branch:
  ```bash
  git checkout feature/<issue_id>-... # Go to the feature branch
  git checkout -b feature/<issue_id>-...-patch-1 # Create patch branch
  # ...Make fixes, commit...
  git checkout feature/<issue_id>-... # Go back to the main feature branch
  git merge feature/<issue_id>-...-patch-1 # Merge the patch branch in
  git branch -d feature/<issue_id>-...-patch-1 # Delete the patch branch
  ```

## 5. Pull Requests (PRs) via `gh` CLI

- **Create:** `gh pr create` (interactive is often easiest).
- **List:** `gh pr list`.
- **View:** `gh pr view <pr_number_or_branch>`.
- **Checkout:** `gh pr checkout <pr_number>`.
- **Diff:** `gh pr diff <pr_number>`.
- **Status/Checks:** `gh pr status`, `gh pr checks <pr_number>`.
- **Comment:** `gh pr comment <pr_number> --body "..."`.
- **Review:** `gh pr review <pr_number>` (options: `--approve`,
  `--request-changes`, `--comment`).

## 6. Tooling Quick Reference Table (`git` & `gh`)

| Action                          | Recommended CLI Command(s)                                      |
| :------------------------------ | :-------------------------------------------------------------- |
| Check Status / Branch           | `git status`, `git branch`                                      |
| Switch Branch                   | `git checkout <branch>`                                         |
| Create Branch                   | `git checkout -b <new_branch>` (from current)                   |
| Update from Remote              | `git fetch origin`, `git pull origin <branch>`                  |
| Stage Changes                   | `git add <file>`, `git add .`, `git add -p` (interactive)       |
| Commit Changes                  | `git commit -m "<Conventional Commit Message>"` or `git commit` |
| Push Changes                    | `git push origin <branch>`, `git push -u origin <branch>`       |
| Create PR                       | `gh pr create`                                                  |
| Checkout PR Locally             | `gh pr checkout <pr_number>`                                    |
| View PR Status / Checks         | `gh pr status`, `gh pr checks <pr_number>`                      |
| Comment/Review PR               | `gh pr comment <pr_number>`, `gh pr review <pr_number>`         |
| List Issues / PRs               | `gh issue list`, `gh pr list`                                   |
| View Issue / PR                 | `gh issue view <id>`, `gh pr view <id>`                         |
| Delete Local Branch             | `git branch -d <branch>`                                        |
| Delete Remote Branch (Optional) | `git push origin --delete <branch>`                             |

---

**Remember:** Always run local validation before committing/pushing. Keep
commits atomic and use Conventional Commit messages. Clean up branches after
merging. Use the CLI!
