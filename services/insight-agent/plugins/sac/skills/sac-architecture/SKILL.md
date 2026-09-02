---
name: sac-architecture
description: Research and design a new or changed SAC Practice. Use for upstream-project assessment, deployment topology, cloud-resource mapping, network, storage, database, high availability, business feasibility, or architecture-contract changes.
---

# SAC Architecture Core

Produce evidence-backed architecture decisions before implementation. This Skill is read-only unless the task
explicitly asks to record an architecture artifact. It never creates Terraform, starts delivery, or substitutes
an unconfirmed guess for a design decision.

Use with `sac-project`. Use it for a new Practice or any change to resource topology, deployment form,
network exposure, data services, storage durability, availability, billing shape, or runtime dependencies.
A small Terraform description or output edit does not need an architecture pass.

## Inputs and evidence

Start with the upstream repository or supplied system requirements and the closest formal Practice. Separate:

- **verified facts** backed by upstream or cloud-provider evidence;
- **inferences** drawn from those facts;
- **assumptions** selected to complete a candidate design;
- **unknowns** that affect architecture and require confirmation.

Verify time-sensitive versions, product availability, Region support, specifications, and pricing when they are
used. Do not use popularity metrics as business evidence. Use `sac-deep-search` only when the decision genuinely
requires multi-source, cross-domain research; it is not a prerequisite for ordinary architecture work.

## Business feasibility for a new Practice

Before designing a new Practice, assess whether it is worth formalizing. Score each dimension from 0 to 10,
distinguishing evidence from inference:

| Dimension | Question | Typical rejection signal |
|---|---|---|
| Service fit | Can it run continuously as a service without required local interaction? | Desktop-only GUI or mandatory local interaction |
| Market value | Is there a clear target user and differentiated cloud solution value? | Internal-only utility or stronger equivalent already covers it |
| Scenario value | Does it solve a concrete user problem better than the current alternative? | No identifiable scenario or demand evidence |
| Cloud value | Does cloud deployment add useful reliability, connectivity, scale, or operations? | Moving it to ECS only adds cost or latency |

Use the equal-weight average as decision input:

- below `4`: do not recommend formalization;
- `4–5.9`: continue only after an explicit strategic override is recorded;
- `6` or above: continue technical assessment, but do not automatically start implementation.

A low score never justifies inventing HA, databases, monitoring, or other resources to improve the result.

## System assessment

Identify and support with evidence:

1. upstream version, license, release unit, official installation path, CPU architecture, and lifecycle;
2. runtime, services, ports, health checks, state, data paths, images, and external dependencies;
3. service relationships and startup order, including database, cache, object storage, model API, or identity;
4. image and package-source reachability for the target site and Region;
5. the HTTPS distribution endpoint, immutable object path, and SHA-256 integrity value for the external bootstrap
   script;
6. backup, restore, upgrade, rollback, logs, monitoring, capacity, and operational limits;
7. authentication, TLS, secret handling, supply chain, data protection, and compliance constraints;
8. the nearest formal repository implementation and every intended deviation.

Do not ask the user to pre-fill values that research can determine. Mark anything not supported by evidence as
an assumption or confirmation item.

## Cloud architecture design

Map each required component to the smallest sufficient cloud resource. The mapping must explain why the
resource exists and which upstream requirement it satisfies.

### Compute and runtime

- Prefer the upstream-supported installation unit and stable release.
- Propose a minimal `standard` topology first; add `ha` only when availability requirements and component
  behavior support it.
- Candidate compute defaults are starting points, not frozen facts: assess China-site ECS from an available
  `x1` family specification and international ECS from a general-purpose specification such as
  `c7n.2xlarge.2`, then verify Region availability and workload fit.

### Network and public access

- Define VPC, subnet, routes, DNS needs, outbound dependencies, ingress purpose, source CIDR, and TLS boundary.
- Current formal practice policy requires an EIP and `bandwidth_size`; record its billing mode and application
  ingress scope explicitly.
- Administrative SSH uses the configured CloudShell `/32` source, never `0.0.0.0/0`.
- Do not expose databases, caches, container daemons, debug endpoints, or control ports publicly.

### Storage and data

- Identify persistent and ephemeral paths separately.
- Define disk type, size, termination behavior, backup, restore, and data-loss boundary.
- Add a managed database, cache, object store, shared filesystem, or load balancer only when requirements justify
  it. Record connectivity, credentials, failure modes, migration, and cost implications.

### High availability

For HA, describe failure domains, replica behavior, state coordination, health checks, traffic distribution,
session handling, data durability, recovery objectives, and upgrade behavior. Multiple instances alone do not
prove high availability.

## Confirmation gate

Present a recommended initial design with defaults, alternatives, risks, and evidence. Confirm only unresolved
choices that materially change the implementation, including as applicable:

- site and Region;
- `standard` or `ha`;
- template and runtime installation strategy;
- external bootstrap-script URL, publication owner, and SHA-256 value;
- public entry, source range, port, and TLS termination;
- compute, storage, database, and billing choices;
- product-specific external dependencies;
- accepted deviations or risks.

Do not repeat questions already answered. Stop before implementation when the remaining gap would cause the
Builder to invent a resource, variable, default, endpoint, dependency, or security decision.

## Architecture contract

Freeze one structured handoff containing:

```text
project and upstream revision
verified facts and evidence
business decision, when this is a new Practice
site, Region, variant, and deployment form
component and service topology
cloud resources and dependency graph
network, ports, CIDRs, DNS, EIP, and TLS boundary
storage, database, backup, restore, and durability
compute image, flavor, disk, billing, and capacity assumptions
runtime installation and startup order
external bootstrap source path, HTTPS object URL, publication owner, and SHA-256 value
variables, fixed values, outputs, and user-visible endpoints
availability, operations, upgrade, and rollback
security decisions and accepted risk
documents and local delivery artifacts
assumptions, deviations, confirmed choices, and remaining blockers
```

Every resource and customer-facing variable must trace to this contract. Return the recommended design, rejected
alternatives, evidence, risks, confirmation record, and implementation-ready contract.
