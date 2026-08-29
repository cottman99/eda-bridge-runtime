# Authenticated Codex/Pi Runtime baseline

Date: 2026-08-30

This is the first fair, sanitized comparison of the narrow Codex profile and
the dedicated Pi EDA profile. Both used GPT-5.5 with low reasoning, the same
Runtime 0.1.0a21 contract, the same ADS and AnsysEM `display4` connections, and
the same final schemas. Runs were interleaved to rotate which Agent went first,
but EDA access remained serial. No raw Agent trace, final response, private
path, customer data, mutation, solve, or GUI action was retained.

## Results

| Case | Codex pass | Pi pass | Codex median | Pi median | Pi wall reduction | Codex reported input | Pi reported input |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Runtime connection discovery | 3/3 | 3/3 | 16.127 s | 7.959 s | 50.6% | 34,633 | 1,489 |
| ADS capability discovery | 3/3 | 3/3 | 20.056 s | 10.656 s | 46.9% | 36,353 | 2,488 |
| AnsysEM capability discovery | 3/3 | 3/3 | 19.916 s | 9.902 s | 50.3% | 34,878 | 2,184 |
| One-turn ADS + AnsysEM discovery | 4/5 | 5/5 | 26.184 s | 13.646 s | 47.9% | 50,821 | 3,303 |

The token columns are the clients' provider-reported input counters. They show
context-load behavior but are not asserted to be identical billing units.

## Findings

1. Pi was about 47-51% faster on all four small read-only cases while returning
   the same Runtime payloads and satisfying the same semantic gates.
2. Transport was about one second per vendor capability read for both clients.
   The difference therefore came primarily from Agent startup and context, not
   SSH or Bridge execution.
3. Pi reported about 93-96% fewer input tokens. Its dedicated launcher loaded
   one thin Runtime extension and five selected Skills, whereas even the narrow
   Codex evaluation profile retained a substantially larger system context.
4. One Codex cross-EDA trial returned without attempting either required tool.
   Two confirmation trials then passed, producing 4/5 overall. Pi passed 5/5.
   This is a useful early reliability signal, not enough evidence for a general
   capability ranking.
5. These cases test disciplined tool selection and low-complexity coordination.
   They do not yet show whether Pi matches Codex on documentation judgment,
   multi-step mutation, durable-job recovery, or complete EDA lifecycles.
