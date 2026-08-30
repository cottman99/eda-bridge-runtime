# Bootstrap experience library

The Bootstrap Experience Library gives a newly installed Agent a small amount
of version-scoped operating experience without turning the Bridge into a memory
manager or a second vendor API. This boundary is normative.

## Responsibilities

Vendor Bridges may ship advisory assets for `intuition`, `action_pattern`,
`workflow`, and `anti_pattern`. Every asset has an evolvable status:
`candidate`, `validated`, `preferred`, or `deprecated`. There is no permanent
`golden` type or directory.

The assets are independent package data. Runtime and vendor adapters do not
import them while executing an EDA request. If the library is absent, corrupt,
or stale, native execution remains available; only Agent guidance is degraded.
The Bridge records the caller's purpose, Context, native-program hash and
summary, scope, state transitions, artifacts, validation, and errors. It does
not infer engineering intent, reinterpret technical success as engineering
success, learn from an episode, or rewrite an asset.

Official host-local, version-matched documentation remains the knowledge
gateway. It is not the long-term experience manager. Until an independent
Engineering Memory Manager exists, development Agents maintain the packaged
bootstrap assets. A future manager may propose, score, promote, deprecate, and
drift-check assets, but the Bridge execution core must not depend on it.

## Retrieval and execution chain

```text
user intent
  -> exact EDA Context
  -> version-matched official documentation
  -> matching experience assets and anti-patterns
  -> Agent-generated official native plan
  -> governed Bridge execution
  -> operation receipt and independent validation
```

An experience asset is advice that can be questioned or outdated. It is not an
API, authorization, capability declaration, or proof of success. The Agent must
still verify official references and the actual Context.

## Asset and manifest contract

Each Markdown asset uses YAML frontmatter. The current parser deliberately
accepts a JSON-compatible YAML subset so verification needs no YAML runtime
dependency. Required fields are `id`, `kind`, `status`, `summary`, `intents`,
`tags`, `applies_to`, `prerequisites`, `recommendation`, `steps`,
`failure_signals`, `validation`, `official_refs`, `evidence_refs`, `confidence`,
`last_verified`, and `supersedes`, plus `schema_version` and the independently
evolvable `asset_version`.

Each vendor package contains `experience_assets/manifest.json`; the manifest
records the schema version, provider, exact asset path, kind, status, summary,
and SHA-256. Raw episodes, customer data, private experience, credentials,
vendor documentation, and private evidence never enter the public library.
Fenced Python, AEL, or pseudocode is illustrative source material and must
never be imported by product code as a stable wrapper.

## Compiled shortcuts

API wrapping is allowed only as a token and reliability optimization for a
validated command group. The experience asset is the semantic source of truth;
the implementation is a compiled shortcut, execution macro, or cached
implementation. It cannot provide a capability that governed native execution
cannot reach.

Every non-infrastructure shortcut declares `implements_asset_id`, asset version
and schema, exact asset content hash, implementation version, applicability,
effect class, parameter schema, validation contract, and the
`governed_native_execution` fallback. A shortcut is preferred only while its
asset is `validated` or `preferred`, its hash and applicability match, and its
runtime probe is healthy. Deprecated or drifted assets automatically make the
shortcut ineligible.

Markdown is never executed. A controlled release-time registration binds an
eligible asset to reviewed product code. The operation receipt records the
asset identity and hash, implementation version, expanded-plan hash or bounded
summary, native-call evidence, and validation result. With no shortcut, the
Agent follows the same official documentation and asset through governed native
execution.
