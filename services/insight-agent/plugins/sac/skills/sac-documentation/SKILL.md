---
name: sac-documentation
description: Generate, maintain, translate, render, and validate SAC deployment guides and solution details from verified implementation facts. Use for new or existing Markdown, zh/en documents, optional DOCX, legacy document conversion, or formal document quality gates.
---

# SAC Documentation

Use this as the single formal entry for SAC documentation. Derive technical facts from verified implementation;
never invent parameters, ports, versions, costs, performance, availability, or validation results.
This Skill is runtime-neutral and contains the shared documentation rules used by every coding-agent adapter.

## Scope

- Generate or maintain Deployment Guide and Solution Details Markdown.
- Produce China-site Chinese and international-site Chinese/English documents.
- Translate while protecting code, commands, paths, URLs, identifiers, versions, and resource IDs.
- Render DOCX only when `project.config.json` sets `require_docx=true` or the user requests it.
- Convert existing Markdown, DOCX, or PDF through the standard document model.
- Run document-only checks; page extraction and marketing/Excel work belongs to `sac-page-enhance`.

## Inputs and truth

Read `sac-project`, the frozen architecture contract or explicit maintenance request, current Terraform and
optional `.extension`, then relevant implementation and quality evidence and existing documents. Truth order is
implementation and configuration, explicit user material, project references, then style samples. Never use
samples as project facts. Skip secrets and build output.

For a small edit, verify only affected facts and preserve unrelated structure. For generation, translation,
conversion, or formal review, use the standard model and pipeline below.

## Required outputs

- Formal Markdown for each requested site, locale, and document type.
- `standard-document.json`, `quality-report.json`, and `manual-review.json` for pipeline work.
- DOCX only when required; its absence must not block a Markdown-only delivery.

Use the repository naming and locale layout defined by `sac-project`. Retain historical names until an
explicit migration is requested.

## Workflow

1. Resolve requested sites, locales, document types, and whether DOCX is required.
2. Extract implementation, architecture, parameter, deployment, validation, security, rollback, and limitation facts.
   For every deployable instance, record the external bootstrap object path, fixed SHA-256, publication owner,
   required HTTPS reachability, install log, and failure diagnosis without exposing credentials or private endpoints.
3. Scan for sensitive values; report location and type, never the value.
4. Build or update the standard model with source, inferred, missing, and confirmation markers.
5. Generate Chinese Markdown; adapt regional facts before producing international Chinese.
6. Translate English using project, product, cloud-service, then global terminology priority.
7. Render all formats from the same model; do not independently rewrite DOCX content.
8. Compare documents with implementation and across locales, then produce quality and manual-review reports.
9. Run the formal project test entry before handing files to local packaging or release review.

## Live pricing contract

When creating or updating **资源与成本规划 / Resources & Cost Planning** or **预估成本 / Estimated Cost**,
invoke `query-huawei-cloud-prices` to systematically query every priced Huawei Cloud resource confirmed
in the verified Terraform:

1. **Map each resource** — identify every billable resource specification (ECS flavor, EVS volume type/size,
   NAT gateway spec, bandwidth, RDS规格, etc.) and its quantity from the verified Terraform and variables.
2. **Query systematically** — for each unique specification, call `query_prices()` with the document site
   (`cn` → `china`, `intl` → `intl`), exact Region ID, and exact resource specification code.
3. **Display three billing modes** — present on-demand (`on-demand`), monthly (`monthly`), and yearly
   (`yearly`) prices returned by the live query in the cost table. Never convert currency, derive a missing
   billing mode, flatten tiered pricing, or copy a price from samples or an older document.
4. **Preserve the raw response** — keep currency, measure units, tiered amounts, and quantity relationships
   exactly as the calculator returns. Label clearly as "参考报价，最终以账单为准 / Reference quotation,
   final invoice prevails" and record the query date.
5. **Handle unresolvable items** — if a product, Region, or exact specification cannot be resolved, mark the
   affected row as `待询价 / Price to be confirmed`, capture the query error in the manual review list, and
   do not substitute an approximate or historical price.

## Hermes official-document contract

For Hermes Agent, read the current official pages before writing: deployment guide
`hermes_01.html` through `hermes_08.html`, and the Huawei Cloud solution-detail page
`deploying-hermes-agent.html`. The deployment guide must cover their ordered information contract:
solution overview; resource and cost planning; preparation including RFS delegation; RFS deployment and
parameter table; first use, model configuration, optional channel integration and verification; RFS
uninstall; glossary. The solution detail must cover Hero/CTA, target customers, three evidence-backed
advantages, architecture and deployment option, three use cases, practice extensions, and service
highlights. Do not copy a fixed price, duration, screen label, model provider, or product feature unless
it remains current in the cited official page and consistent with the implemented template and upstream repository.

Retain costs, durations, percentages, performance, customer counts, and similar numbers only with a verifiable
source. Cloud-resource prices must additionally satisfy the live pricing contract above. Otherwise remove them or
mark them `待业务确认`. Record unreliable PDF structure as a review item.

## CLI routing

In this source repository, use `.venv-sac/bin/python` and the root `scripts/` tree. In an npm-initialized
host, use its isolated `.sac/tooling` copy instead:

```bash
python -m venv .venv-sac
.venv-sac/bin/python -m pip install -r .sac/tooling/requirements-test.txt
```

Do not claim DOCX or formal-gate execution when tooling is not present; report that capability as
blocked. Document generation commands are provided by installed tooling; available subcommands are
`analyze`, `generate`, `translate`, `render-word`, `validate`, `convert`.

Default to offline processing. External models or endpoints require explicit configuration and applicable data
authorization. If unavailable, preserve deterministic outputs and report the missing semantic work.

## Quality gate

Block handoff for invalid schema, missing required Markdown or official-section coverage, secret exposure,
broken protected tokens, implementation/parameter/URL conflicts, or unmarked unreliable conversion. Block
on DOCX errors only when DOCX is required. Wording and optional sections may be warnings but must enter
manual review. Run `.venv-sac/bin/python -m scripts.tests.runner`, or the npm-host equivalent
`PYTHONPATH=.sac/tooling .venv-sac/bin/python -m scripts.tests.runner`.

Return files changed, sources checked, commands run, warnings, blockers, and required human review.
