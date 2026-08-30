# Alpha release contract

## Product promise

Runtime gives local and SSH EDA Bridges one request, identity, transport, job,
ledger, transaction, and evidence envelope. It defines the governed native batch
contract and the independent Bootstrap Experience Library contract without
implementing a second ADS, AEDT, or future-vendor API.

Vendor packages may expose three execution surfaces: core infrastructure
primitives, universal governed native execution, and asset-bound compiled
shortcuts. A shortcut only compresses a validated command group. It must not be
the sole route to an official capability.

## Experience boundary

The Runtime wheel carries the asset and compiled-shortcut schemas plus offline
validation and read-only retrieval helpers. Vendor Bridges carry their own
hashed assets. Runtime and adapters do not execute Markdown, infer engineering
intent, learn from receipts, or mutate experience. Missing or corrupt assets
degrade advisory retrieval only; Context, transport, jobs, ledgers, and native
execution remain available.

A future independent Engineering Memory Manager may propose, score, promote,
deprecate, and drift-check assets. No Runtime execution path may depend on that
future service.

## Required gates

- full Python and Pi integration tests plus Ruff;
- clean wheel contents and a fresh installation check;
- native-batch schema, fingerprint, scope, transaction, timeout, validation,
  and failure-path tests;
- experience schema, frontmatter, manifest hash, degraded-library, and
  compiled-shortcut binding tests;
- plugin and Pi Skill routing that preserves official-doc and governed-native
  fallbacks;
- no customer data, vendor manuals, credentials, private hosts, personal paths,
  raw conversations, or unredacted commands in public artifacts;
- one sanitized real-EDA observe and staged/fresh-reopen acceptance for each
  newly supported governed native runtime.

## Deliberately unclaimed

AST policy lint and declared scope are accidental-risk controls, not a hostile
code sandbox. Runtime does not decide engineering correctness, select vendor
semantics, or guarantee that an experience remains current without version and
runtime verification.
