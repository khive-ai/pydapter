---
title: "Roo Lite"
by: "Ocean"
scope: "project"
created: "2025-05-05"
updated: "2025-05-05"
version: "1.0"
description: >
  A lightweight response format for all tasks, designed to keep token costs low
  and encourage broad thinking before acting. This format is tool-agnostic and
  allows for task-specific templates to be layered on top.
---

# Global Response Format

> Use this for every turn, no matter the task. Add extra sections only if the
> task itself demands it.

## 1. Why a Lite global response format?

- Forces the model to think broadly before acting.
- Stays tool-agnostic—no CI, YAML, or schema baggage.
- Keeps token-cost low (≈ 70–120 tokens per turn)
- Leaves room for task-specific templates (docs, reviews, PRs) to layer on their
  own details.

---

## 2. The only rule

- **Structured reasoning format.**: Always begin your reply with a
  <multi-reasoning> block containing 3–5 concise, clearly-labeled perspectives.
  After that block, write the answer however you like.

```
<multi-reasoning>
1. [^Spec]        Reason | Action | Outcome
2. [^Impl]        ...
3. [^Validation]  ...
</multi-reasoning>

<your main answer continues here>
```

---

## 3. Allowed perspective tags

| tags          | when to use them                   | e.g.                         |
| ------------- | ---------------------------------- | ---------------------------- |
| [^Spec]       | Clarify requirements & constraints | `What does 'done' mean?`     |
| [^Impl]       | Pick algorithms, code shape        | `How will we build it?`      |
| [^Validation] | Think about tests & edge cases     | `How will we know it works?` |
| [^Risk]       | Spot failure modes & security      | `What can break?`            |
| [^System]     | View dependencies & feedback loops | `How does this fit in?`      |
| [^Efficiency] | Optimise speed/cost                | `Can we do it leaner?`       |
| [^User]       | Consider human impact & UX         | `Who touches this, and how?` |

> - Minimum: use Spec + Impl + Validation.
> - Optional: add up to three more relevant tags.
> - Advanced Optional: add up to three more reasoning perspectives (see below).

---

## 4. Micro-syntax inside each bullet

```
[^Tag] Reason: … | Action: … | Outcome: …
```

---

## 5. Advanced reasoning perspectives (optional)

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
