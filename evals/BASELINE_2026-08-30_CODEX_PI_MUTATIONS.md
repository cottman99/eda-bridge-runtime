# Codex and Pi disposable mutation acceptance

Date: 2026-08-30

This sanitized three-trial-per-Agent acceptance checks whether each Agent can create one disposable
EDA artifact and then repeat the entire request exactly enough for Runtime to reuse the original
result. Trials are interleaved and use independent targets and identities. Purpose, connection,
operation, payload, wait policy, and idempotency key are all part of the request identity.

| Case | Agent | Result | Calls | Actual creations | Reused runs | Wall | Runtime + transport + EDA | Outside transport |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ADS workspace create + replay | Codex | 2/3 passed | 3 per executed trial | 1 per passing trial | 1 per passing trial | 32.109 s median | 1.890 s median | 30.172 s median |
| ADS workspace create + replay | Pi | 3/3 passed | 3 each | 1 each | 1 each | 16.605 s median | 1.844 s median | 14.825 s median |
| AnsysEM project create + replay | Codex | 3/3 passed | 3 each | 1 each | 1 each | 67.000 s median | 39.437 s median | 28.971 s median |
| AnsysEM project create + replay | Pi | 3/3 passed | 3 each | 1 each | 1 each | 56.672 s median | 38.953 s median | 16.515 s median |

Every executed passing trial used one capability read, one real mutation, and one exact replay. The
replay returned the original Runtime Run rather than launching a second vendor mutation. Codex's
first ADS trial made zero tool attempts but claimed success; strict scoring classified it as
`agent_reported_unverified_success`, so it did not create or replay anything and is not attributed
to Runtime, transport, Bridge, or ADS. This matches the same Agent-side zero-call class previously
seen in one Momentum trial.

The evidence supports a general rule: idempotency should remain whole-request identity, while
Skills and evaluator cases should tell the Agent to replay the complete request byte-for-byte in
meaning. Weakening Runtime identity to ignore explanatory fields would hide intent drift and make
the audit record less trustworthy.

The aggregate-only repeated baseline is stored in
`evals/baselines/codex-pi-gpt55-low-runtime-a23-l3-mutations-repeated-20260830.json`.
