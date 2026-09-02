---
name: sac-project
description: Apply repository-wide SAC scope, source-of-truth, practice layout, authorization, and minimal-change rules. Use whenever a task changes or evaluates a formal Solution Practice or shared SAC asset.
---

# SAC Project Core

SAC is a solution-practice engineering package. Its core outcome is verified Terraform plus the documents
and local delivery evidence needed to hand that Terraform to a user. It does not call a model, provide an
agent runtime, create cloud resources, or prove that a static-checked template deployed successfully.

This Skill is runtime-neutral. It defines project rules shared by every coding-agent adapter; platform
discovery, context loading, delegation, and invocation belong outside this Skill.

## Source of truth

Use repository truth in this order:

1. `project.config.json` for skills registry and agent capabilities;
2. `skills/` for canonical SKILL.md business rules;
3. executable tests and quality scripts for current static evidence;
4. `skills/reference/` and `docs/contracts/` for engineering rules;
5. README and generated indexes as presentation only.

In an installed host without a root `project.config.json`, use `.sac/project.config.json`.
Never treat a manually maintained score, label, status, or narrative as an automatically verified result.

## Formal and experimental scope

- A formal Practice is a project listed in `project.config.json` and backed by `practices/<project>/`.
- Keep an unlisted candidate under `.var/candidates/practices/` until formal admission is explicitly approved.
- `skills/reference/` is read-only unless the user explicitly changes that scope.
- Runtime adapters, historical reports, and local archives do not define formal practice scope.

Project IDs are lowercase hyphenated names. The canonical implementation dimensions are `site → region`,
with `variant` only when one Region has multiple deployment forms:

```text
practices/<project>/<cn|intl>/<region>/deploying-<project>_vN.tf
practices/<project>/<cn|intl>/<region>/<variant>/deploying-<project>_vN.tf
practices/<project>/cn/docs/*.md
practices/<project>/intl/docs/{zh-cn,en-us}/*.md
```

A Region-level template is implicitly `standard`; do not add a `standard/` directory unless variants coexist.
Each deployable instance directory contains exactly one loadable Terraform file and no redundant `terraform/`
wrapper. Locale is a documentation dimension, not an implementation dimension. Empty project, site, Region,
and variant directories are forbidden.

Practice source contains deployable Terraform, one external bootstrap script per deployable instance, optional
`.extension`, and required site documents. Evidence, extracted upstream files, duplicate archives, and generated
packages stay outside `practices/`.

## Deliverables and boundaries

For a complete new Practice, the required content is:

- deployable Terraform for every requested `site/region[/variant]`;
- `scripts/install_<project>.sh` for every deployable instance;
- a Deployment Guide for every requested site;
- Solution Details for every requested site.

An optional `.extension`, configured DOCX, deterministic archive, and SHA-256 checksum are packaging or
presentation outputs. They never replace the three required deliverables. Existing formally approved legacy
installers may remain only where `project.config.json` records the exact exception; an exception is not a
pattern for new work.

Cloud changes, external publication, Git commit or push, version changes, and package publication require
separate explicit authorization. Local generation and static validation never imply cloud success or
production readiness.

Local releases use `vX.Y.Z`. When a version change is authorized, synchronize every configured version record.
Public names, commands, fields, and paths must not silently disappear in a patch or minor release.

## Capability roles and task flow

Architect, Builder, and Reviewer are capability roles, not three processes that every task must start:

- **Architect** researches, makes architecture decisions, records assumptions, and freezes the contract.
- **Builder** maps an approved change to Terraform and documents, runs local checks, and fixes findings.
- **Reviewer** independently checks implementation, security, architecture, documents, and release evidence.

Choose the smallest sufficient flow:

```text
small maintenance     Builder
normal maintenance    Builder → Reviewer
architecture change   Architect → Builder → Reviewer
new Practice          Architect → Builder → Reviewer → Builder Fix when needed
review only            Reviewer
```

Only independent tasks with non-overlapping file ownership may run concurrently. Delegation mechanics are a
runtime-adapter concern.

## Change rules

- Preserve user changes and inspect every caller or reference before moving or renaming an asset.
- Make the change that enables **successful deployment**. Prefer minimal changes but do not skip reliability
  measures (startup ordering, health checks, dependency waits) for the sake of minimalism.
- Do not change resource topology, defaults, dependencies, ingress, storage durability, billing, or bootstrap
  behavior unless the architecture contract or deployment reliability requires it.
- Start a new candidate at `_v1`; use the next `_vN` for behavior changes. Candidate and formal names never
  coexist, and promotion requires explicit approval.
- Never write credentials, tokens, private endpoints, or private bucket data to source, artifacts, or logs.
- Record static checks and unrun cloud checks separately. Do not convert an assumption into a fact.
- Record accepted risk only in the project policy or architecture contract, with scope and evidence.

## Core routing

- New systems, topology, cloud mapping, network, data, availability, or architecture changes:
  `sac-architecture`.
- Terraform, variables, outputs, modules, `user_data`, dependencies, maintenance, or local packaging:
  `sac-implementation`.
- Review, validation, security, consistency, impact, or release readiness: `sac-quality`.
- Deployment guides, parameters, architecture descriptions, translations, DOCX, or document checks:
  `sac-documentation`.

Load only the Skills required by the selected flow. Optional research, pricing, and page-enhancement Skills
remain outside the default Terraform path.
