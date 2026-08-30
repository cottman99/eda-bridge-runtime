# Runtime-owned EDA resources

EDA Runtime is the normal path for local and SSH-hosted EDA operations. A vendor Bridge may create
an interactive process that intentionally outlives one request. Such a result uses
`eda-runtime.resource/v1` and states its resource id, kind, ownership, lifecycle state, and typed
release operation.

Only a resource marked `runtime-owned` may be released through that operation. Each vendor Bridge
must verify its own durable ownership evidence and the exact live identity before closing it. A
reused or user-owned application is never claimed merely because Runtime can see it. Force-killing
is not a release mechanism.

The local Runtime audit stores a token-free `eda-runtime.resource-view/v1` projection. It keeps the
resource id, kind, ownership, state, and release operation, but never copies release handles, raw
paths, or a remote vendor database. Remote run ids and bounded evidence references are materialized
into the same local audit record, so normal timing and behavior analysis does not require replaying
the Agent conversation.

When an operation genuinely has no typed Runtime route, the caller records a bounded bypass fact:

```text
eda-runtime audit bypass --purpose "..." --lane gui --reason "..." --outcome passed
```

The bypass record contains motive, lane, outcome, and actor facts. It deliberately does not record
the raw shell command or GUI input. Vendor Skills should prefer capability discovery and typed
operations, and use this lane only when the installed Bridge advertises no safe equivalent.
