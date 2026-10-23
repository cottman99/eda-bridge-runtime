# EDA capability model

This document defines how Runtime and vendor Bridges expand EDA capability. It
is normative for architecture and product decisions.

## The Bridge is not a second vendor API

ADS, AEDT, and future EDA products already expose large, versioned Python, AEL,
native, and command APIs. Re-encoding every vendor operation as a Bridge
operation would create a permanently incomplete second API. It would also make
an ordinary new vendor-API use require a Bridge release.

Capability therefore comes primarily from this loop:

```text
closest applicable experience
        -> version-matched official docs for unresolved or changed behavior
        -> Agent writes official vendor code
        -> governed native execution in exact EDA Context
        -> independent readback, validation, and evidence
```

The Bridge and Runtime own the reliability envelope around official code. They
do not replace the official API inside that envelope.

A packaged bootstrap experience library may help an Agent choose a proven
official route without rediscovering every operational detail. It remains
advisory and independently versioned: it does not increase official API reach,
authorize execution, or prove workflow success. See
[`EXPERIENCE_LIBRARY.md`](EXPERIENCE_LIBRARY.md).

## Five different coverage claims

Never collapse these dimensions into one capability count:

| Dimension | Meaning |
| --- | --- |
| Knowledge coverage | Which version-matched official documentation the Agent can retrieve with bounded evidence |
| Official API reach | Which official runtimes and languages the Bridge can invoke in the selected installation and Context |
| Generic execution coverage | Which Context, scope, transaction, timeout, cancellation, logging, readback, and validation controls work for arbitrary official code |
| Default supported coverage | Which generic lanes and certified workflows are enabled by default with a maintained safety boundary |
| Validated workflow coverage | Which exact end-to-end engineering journeys passed retained real-EDA acceptance |

A validated recipe proves its named journey. It does not define the maximum
reach of the official API, and official API reach does not prove that every
possible workflow is validated.

## Four operation classes

Every advertised operation must be classified as one of:

1. **Bridge infrastructure** — installation discovery, Context, connection,
   workspace/project/session identity, lifecycle, jobs, reconciliation,
   staging, rollback, promotion, audit, compact run receipts, and
   artifact/evidence handling.
2. **Generic native execution** — official Python, AEL, or native programs inside
   an exact Context and a governed effect boundary. This is the main extension
   path for vendor functionality.
3. **Certified workflow** — an asset-bound compiled shortcut for a
   high-frequency, versioned, tested command group. The asset is semantic truth;
   the implementation only compresses tokens and reduces transcription risk.
4. **Acceptance probe** — a narrow diagnostic or example used to prove one
   environment or contract. It is not a top-level product capability merely
   because it is callable.

Certified workflows remain valuable. They are shortcuts and quality baselines,
not the only way to reach EDA functionality. An Agent discovers one through the
applicable experience asset; the bare operation list must not anchor the Agent
to wrappers as the vendor's capability boundary.

Adapter operation descriptors are deterministic request, safety, and lifecycle
contracts. They answer "how may this callable route be invoked safely?", not
"what can this EDA product do?" Explicit descriptor discovery is diagnostic
metadata, not a routine semantic routing gate.

Runtime retains the complete descriptor set internally for deterministic safety
checks and compatibility calls. Ordinary Agent discovery projects only core
infrastructure, live-edit, and generic-native contracts. Certified workflows
and acceptance probes are absent from that view. A certified implementation
becomes model-visible only when the exact `experience.get` result returns its
binding.

When the operation id is already known but its typed input contract is not,
`eda.capabilities` accepts that exact operation selector and projects one core
descriptor. This is response minimization, not semantic routing or a capability
boundary; the complete descriptor cache remains available internally for
deterministic validation.

The execution surface therefore has three distinct parts: core infrastructure
primitives, compiled workflows, and universal governed native execution. Release
validation binds each compiled workflow to reviewed experience. Runtime validates
the compiled version/profile contract; missing or drifted Markdown removes its
advisory recommendation, not its executable availability. Inapplicable compiled
contracts use the native route.

## What generic native execution must govern

A generic native request is not an unrestricted shell. Before execution it
must declare and bind:

- the exact connection, installation, display, session, workspace/project,
  design, and official runtime;
- whether the request observes or mutates, plus its intended filesystem and EDA
  object scope;
- a bounded official-language program and its content fingerprint;
- timeout, cancellation, output-size, and artifact limits;
- staging/copy strategy, source fingerprint, idempotency, and promotion policy
  for mutations;
- postconditions, fresh-session validation when applicable, and artifact
  checks.

Runtime records purpose, identity, timing, state, and evidence. The vendor
Bridge selects and launches the correct official runtime, enforces the declared
scope as far as that EDA permits, and performs vendor-specific lifecycle and
readback. A governed lane reduces accidental risk; it is not a security sandbox
against hostile Python unless an actual OS sandbox is present.

The common reusable unit is the execution envelope and transaction lifecycle,
not a growing vocabulary of `add_instance`, `add_wire`, plot types, or solver
cases.

The first shared wire contract is
[`eda.native-program/v1`](schemas/native-program-v1.schema.json). It validates the
program fingerprint, official runtime selector, observe-versus-staged effect,
declared read/write paths, source fingerprints, fresh-reopen policy, validation
program, artifacts, timeout, and output bound. Vendor Bridges remain
responsible for enforcing those declarations against their real workspace or
project format.

`program_id`, `program.sha256`, and `validation.program.sha256` are derived fields.
An Agent may omit them: trusted Runtime recomputes program digests from the
exact UTF-8 source and materializes a deterministic program identifier from
the rest of the normalized request. A supplied identifier is preserved, while a
supplied fingerprint must match. Runtime does not derive effect, scope, paths,
transaction policy, limits, or engineering validation. Capability descriptors
for this generic lane may declare `agent_required` separately from
`derived_fields` so an Agent need not manufacture those bookkeeping values; this
is descriptive metadata and does not weaken Runtime validation.

## Route order

Use this order:

1. the official same-session live API when the user copied GUI Context;
2. governed official native execution, reusing applicable experience and using
   version-matched docs only for unresolved or changed behavior;
3. an experience-referenced certified workflow only when its exact binding
   matches and same-task evidence shows a concrete advantage;
4. bounded GUI assistance only after official API routes are genuinely absent;
5. manual external action.

Every official script uses `native.execute`; a lifecycle gap is an explicit
unsupported-mode result, not a reason to retain a parallel executor.

Do not add a new certified workflow merely to avoid improving the generic
execution envelope. Promote a recipe only when frequency, complexity,
repeatability, or risk justifies its maintenance cost.

## Promotion test for a certified workflow

A workflow earns a stable operation only when it is common enough to save
meaningful engineering effort and has a versioned contract, deterministic
targeting, safe retries, independent readback, real-runtime evidence, and a
clear support boundary. A single missing vendor method, plot kind, component,
or geometry primitive is not sufficient justification.

## Compiled workflow independence

Release checks bind reviewed workflow code to the packaged experience hash. At execution time, code validates its own compiled version/profile contract without reading Markdown. Missing or changed assets affect advisory eligibility only. Native execution and retained compiled workflows remain callable through the same Worker admission path.
