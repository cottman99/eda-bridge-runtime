# Codex and Pi disposable mutation acceptance

Date: 2026-08-30

This sanitized single-run acceptance checks whether each Agent can create one disposable EDA
artifact and then repeat the entire request exactly enough for Runtime to reuse the original result.
Purpose, connection, operation, payload, wait policy, and idempotency key are all part of the
request identity.

| Case | Agent | Result | Calls | Actual creations | Reused runs | Wall | Runtime + transport + EDA | Outside transport |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ADS workspace create + replay | Codex | passed | 3 | 1 | 1 | 32.090 s | 1.797 s | 30.293 s |
| ADS workspace create + replay | Pi | passed | 3 | 1 | 1 | 18.546 s | 1.922 s | 16.624 s |
| AnsysEM project create + replay | Codex | passed | 3 | 1 | 1 | 72.634 s | 44.780 s | 27.854 s |
| AnsysEM project create + replay | Pi | passed | 3 | 1 | 1 | 55.065 s | 40.326 s | 14.739 s |

All four cases used one capability read, one real mutation, and one exact replay. The replay
returned the original Runtime Run rather than launching a second vendor mutation. This closes the
earlier observed Agent-side risk where changing only the purpose text correctly produced an
idempotency conflict.

The evidence supports a general rule: idempotency should remain whole-request identity, while
Skills and evaluator cases should tell the Agent to replay the complete request byte-for-byte in
meaning. Weakening Runtime identity to ignore explanatory fields would hide intent drift and make
the audit record less trustworthy.
