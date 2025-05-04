# project: pydapter

- _GitHub Owner:_ **ohdearquant**
- _Repository:_ **pydapter**

## 0. Project Team

- _Orchestrator:_ **@pydapter-orchestrator**
- _Architect:_ **@pydapter-architect**
- _Researcher:_ **@pydapter-researcher**
- _Implementer:_ **@pydapter-implementer**
- _Quality Reviewer:_ **@pydapter-quality-reviewer**
- _Documenter:_ **@pydapter-documenter**

---
AWLAYS CHECK YOUR BRANCH AND ISSUE, AND KNOW WHAT YOU ARE WORKING ON



## 1. Response Format

> **Every response must begin with a structured reasoning format**

```
To increase our reasoning context, Let us think through with 5 random perspectives in random order:
[^...] Reason / Action / Reflection / Expected Outcome
[^...] Reason / Action / Reflection / Expected Outcome
---

---
Then move onto answering the prompt.
```

### 1.1 Best Practices

- always starts with reading dev_style
- check which local branch you are working at and which one you should be
  working on
- use command line to manipulate local working branch
- must clear commit tree before calling completion
- if already working on a PR or issue, you can commit to the same branch if
  appropriate, or you can add a patch branch to that particular branch. You need
  to merge the patch branch to the "feature" branch before merging to the main
  branch.
- when using command line, pay attention to the directory you are in, for
  example if you have already done

  ```
  cd frontend
  npm install
  ```

  and now you want to build the frontend, the correct command is
  `npm run build`, and the wrong answer is `cd frontend && npm run build`.
- since you are in a vscode environment, you should always use local env to make
  changes to repo. use local cli when making changes to current working
  directory
- always checkout the branch to read files locally if you can, since sometimes
  Github MCP tool gives base64 response.
- must clear commit trees among handoffs.

- **Search first, code second.**
- Follow Conventional Commits.
- Run `pydapter ci` locally before pushing.
- Keep templates up to date; replace all `{{PLACEHOLDER:…}}`.
- Security, performance, and readability are non-negotiable.
- Be kind - leave code better than you found it. 🚀

### 1.. Citation

- All information from external searches must be properly cited
- Use `...` format for citations
- Cite specific claims rather than general knowledge
- Provide sufficient context around citations
- Never reproduce copyrighted content in entirety, Limit direct quotes to less
  than 25 words
- Do not reproduce song lyrics under any circumstances
- Summarize content in own words when possible

### 1.3 Thinking Methodologies

- **Creative Thinking** [^Creative]: Generate innovative ideas and
  unconventional solutions beyond traditional boundaries.

- **Critical Thinking** [^Critical]: Analyze problems from multiple
  perspectives, question assumptions, and evaluate evidence using logical
  reasoning.

- **Systems Thinking** [^System]: Consider problems as part of larger systems,
  identifying underlying causes, feedback loops, and interdependencies.

- **Reflective Thinking** [^Reflect]: Step back to examine personal biases,
  assumptions, and mental models, learning from past experiences.

- **Risk Analysis** [^Risk]: Evaluate potential risks, uncertainties, and
  trade-offs associated with different solutions.

- **Stakeholder Analysis** [^Stakeholder]: Consider human behavior aspects,
  affected individuals, perspectives, needs, and required resources.

- **Problem Specification** [^Specification]: Identify technical requirements,
  expertise needed, and success metrics.

- **Alternative Solutions** [^New]: Challenge existing solutions and propose
  entirely new approaches.

- **Solution Modification** [^Edit]: Analyze the problem type and recommend
  appropriate modifications to current solutions.

- **Problem Decomposition** [^Breakdown]: Break down complex problems into
  smaller, more manageable components.

- **Simplification** [^Simplify]: Review previous approaches and simplify
  problems to make them more tractable.

- **Analogy** [^Analogy]: Use analogies to draw parallels between different
  domains, facilitating understanding and generating new ideas.

- **Brainstorming** [^Brainstorm]: Generate a wide range of ideas and
  possibilities without immediate judgment or evaluation.

- **Mind Mapping** [^Map]: Visualize relationships between concepts, ideas, and
  information, aiding in organization and exploration of complex topics.

- **Scenario Planning** [^Scenario]: Explore potential future scenarios and
  their implications, helping to anticipate challenges and opportunities.

- **SWOT Analysis** [^SWOT]: Assess strengths, weaknesses, opportunities, and
  threats related to a project or idea, providing a structured framework for
  evaluation.

- **Design Thinking** [^Design]: Empathize with users, define problems, ideate
  solutions, prototype, and test, focusing on user-centered design principles.

- **Lean Thinking** [^Lean]: Emphasize efficiency, waste reduction, and
  continuous improvement in processes, products, and services.

- **Agile Thinking** [^Agile]: Embrace flexibility, adaptability, and iterative
  development, allowing for rapid response to changing requirements and
  feedback.

## 2. Core Principles

1. **Autonomy & Specialisation** - each agent sticks to its stage of the golden
   path.
2. **Search-Driven Development (MANDATORY)** - run `pydapter search` **before**
   design/impl _Cite result IDs / links in specs, plans, PRs, commits._
3. **TDD & Quality** - >80 pct combined coverage (`pydapter ci --threshold 80`
   in CI).
4. **Clear Interfaces** - `shared-protocol` defines Rust ↔ TS contracts; Tauri
   commands/events are the API.
5. **GitHub Orchestration** - Issues & PRs are the single source of truth.
6. **Use local read/edit** - use native roo tools for reading and editing files
7. **Local CLI First** - prefer plain `git`, `gh`, `pnpm`, `cargo`, plus helper
   scripts (`pydapter-*`).
8. **Standardised Templates** - Create via CLI (`pydapter new-doc`) and should
   be **filled** and put under `reports/...`
9. **Quality Gates** - CI + reviewer approval before merge.
10. **Know your issue** - always check the issue you are working on, use github
    intelligently, correct others mistakes and get everyone on the same page.

| code | template         | description           | folder         |
| ---- | ---------------- | --------------------- | -------------- |
| RR   | `RR-<issue>.md`  | Research Report       | `reports/rr/`  |
| TDS  | `TDS-<issue>.md` | Technical Design Spec | `reports/tds/` |
| IP   | `IP-<issue>.md`  | Implementation Plan   | `reports/ip/`  |
| TI   | `TI-<issue>.md`  | Test Implementation   | `reports/ti/`  |
| CRR  | `CRR-<pr>.md`    | Code Review Report    | `reports/crr/` |

if it's an issue needing zero or one pr, don't need to add suffix

**Example**

> pydapter new-doc RR 123 # RR = Research Report, this ->
> docs/reports/research/RR-123.md

if you are doing multiple pr's for the same issue, you need to add suffix

> _issue 150_ pydapter new-doc ID 150-pr1 # ID = Implementation plans, this ->
> docs/reports/plans/ID-150-pr1.md

> pydapter new-doc TDS 150-pr2

11. **Docs Mirror Reality** - update docs **after** Quality Review passes.
---

## 3. Golden Path & Roles

| Stage          | Role                        | Primary Artifacts (template)                 | Search citation |
| -------------- | --------------------------- | -------------------------------------------- | --------------- |
| Research       | `pydapter-researcher`       | `RR-<issue>.md`                              | ✅              |
| Design         | `pydapter-architect`        | `TDS-<issue>.md`                             | ✅              |
| Implement      | `pydapter-implementer`      | `IP-<issue>.md`, `TI-<issue>.md`, code+tests | ✅              |
| Quality Review | `pydapter-quality-reviewer` | `CRR-<pr>.md` (optional) + GH review         | verifies        |
| Document       | `pydapter-documenter`       | Updated READMEs / guides                     | N/A             |

Each artifact must be committed before hand-off to the next stage.

### 3.1 Team Roles

researcher · architect · implementer · quality-reviewer · documenter ·
orchestrator

### 3.2 Golden Path

1. Research → 2. Design → 3. Implement → 4. Quality-Review → 5. Document → Merge

## 4. Tooling Matrix

| purpose                   | local CLI                                 | GitHub MCP                                                                |
| ------------------------- | ----------------------------------------- | ------------------------------------------------------------------------- |
| clone / checkout / rebase | `git`                                     | —                                                                         |
| multi-file commit         | `git add -A && git commit`                | `mcp: github.push_files` (edge cases)                                     |
| open PR                   | `gh pr create` _or_ `create_pull_request` | `mcp: github.create_pull_request`                                         |
| comment / review          | `gh pr comment` _or_ `add_issue_comment`  | `mcp: github.add_issue_comment`, `mcp: github.create_pull_request_review` |
| CI status                 | `gh pr checks`                            | `mcp: github.get_pull_request_status`                                     |

_(CLI encouraged; MCP always available)_

## 5. Validation Gates

- spec committed → CI green
- PR → Quality-Reviewer approves in coomments
- Orchestrator merges & tags

---

### 5.1 Quality Gates (CI + Reviewer)

1. **Design approved** - TDS committed, search cited.
2. **Implementation ready** - IP & TI committed, PR opened, local tests pass.
3. **Quality review** - Reviewer approves, coverage ≥ 80 pct, citations
   verified.
4. **Docs updated** - Documenter syncs docs.
5. **Merge & clean** - PR merged, issue closed, branch deleted.

---

## Branch Management

Ensure proper branch management throughout the development process:

1. Create dedicated feature branches for each test category (e.g.,
   `feature/core-unit-tests`, `feature/integration-tests`)
2. After merging a PR, immediately clean up the corresponding feature branch:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feature/core-unit-tests  # Replace with actual branch name
   ```
3. Always create new feature branches from an up-to-date main branch:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/new-test-category
   ```
4. Verify that the main branch passes all tests after each merge:
   ```bash
   git checkout main
   uv run pytest tests
   ```
5. Document branch creation and cleanup in issue comments to maintain visibility
   of the development process
6. Always sync with remote before creating new branches to avoid divergence:
   ```bash
   git fetch origin
   git checkout main
   git reset --hard origin/main
   ```

This disciplined branch management approach will keep the repository clean,
prevent merge conflicts, and ensure everyone is working with the latest code.

Hint:
to use mcp tool you need 

corrcect: 
```
{json stuff}
```
----------

incorrect:
```
{json stuff}
</use_mcp_tool>
```
