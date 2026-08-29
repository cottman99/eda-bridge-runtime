# Codex and Pi EDA evaluation summary

Date: 2026-08-30

This page consolidates the sanitized comparison ladder. Repeated rows use three or five trials;
the remaining engineering lifecycle rows are one-run functional acceptance and are not yet
statistical performance claims. Both clients used the GPT-5.5 model family with low reasoning and
the same Runtime/Bridge contracts.

| Level and case | Sample | Codex wall | Pi wall | Pi wall reduction | Dominant boundary |
| --- | --- | ---: | ---: | ---: | --- |
| L0 ADS ambiguity guard | 3 each; Codex 2/3, Pi 3/3 | 10.722 s | 8.823 s | 17.7% | Agent/client only |
| L0 AnsysEM ambiguity guard | 3 each; both 3/3 | 13.148 s | 9.036 s | 31.3% | Agent/client only |
| L0 installed connection discovery | 1 each | 16.982 s | 9.311 s | 45.2% | Agent/client |
| L1 ADS capabilities | 3 each | 20.056 s | 10.656 s | 46.9% | Agent/client |
| L1 AnsysEM capabilities | 3 each | 19.916 s | 9.902 s | 50.3% | Agent/client |
| L2 cross-EDA capabilities | 5 each | 26.184 s | 13.646 s | 47.9% | Agent/client |
| L2 ADS session status | 3 each | 21.955 s | 10.868 s | 50.5% | Agent/client |
| L4 ADS documentation evidence | 3 each | 23.118 s | 13.978 s | 39.5% | Agent/client plus retrieval |
| L4 AnsysEM documentation evidence | 3 each | 23.724 s | 13.970 s | 41.1% | Agent/client plus retrieval |
| L3 ADS create plus exact replay (Codex 2/3; Pi 3/3) | 3 each | 32.109 s | 16.605 s | 48.3% | Agent/client |
| L3 AnsysEM create plus exact replay | 3 each, both 3/3 | 67.000 s | 56.672 s | 15.4% | AEDT lifecycle |
| L5 ADS structured-design plan | 3 each, both 3/3 | 30.135 s | 18.548 s | 38.5% | Agent/client |
| L5 AnsysEM project-evidence plan | 3 each, both 3/3 | 90.871 s | 84.140 s | 7.4% | AEDT lifecycle |
| L5 AnsysEM candidate begin/abort | 1 each, both passed | 85.011 s | 67.829 s | 20.2% | Mixed Agent and AEDT lifecycle |
| L6 generated-input Momentum solve (Codex 2/3; Pi 3/3) | 3 each | 38.814 s | 21.701 s | 44.1% | Mixed Agent and solver |
| L6 one-turn ADS plus AnsysEM | 3 each, both 3/3 | 103.691 s | 92.718 s | 10.6% | AEDT lifecycle |

An alpha.26 public-install spot check is retained separately from the repeated rows above. With one
trial per Agent and vendor, Pi completed ADS/AnsysEM capability reads in 9.375/8.984 seconds and
Codex in 16.375/13.266 seconds. It also exposed and corrected an ambiguous `operation_count` gate:
Codex had reported one tool call instead of the nine/fourteen supported operations, while Pi had
reported the intended values. The case now states the semantic meaning and rejects a count of one
without pinning vendor-version totals.

The same installed profiles then ran bounded ADS and AnsysEM documentation evidence cases. Pi
passed both first attempts; Codex passed AnsysEM but made zero calls and explicitly failed its first
ADS attempt before passing an independent retry. Successful clients selected identical bounded
source/excerpt counts. This is further evidence for Pi as the default typed executor and for keeping
zero-call Agent failures visible instead of automatically rewriting them as Bridge or retrieval
failures.

Installed-profile L2 spot checks also passed: both clients returned the same 13-session ADS fact
from a 20-character projected result, and both coordinated ADS plus AnsysEM capability discovery in
one turn with two sequential Runtime calls and the correct nine/fourteen supported-operation
counts. Pi completed these in 9.797/11.954 seconds versus Codex's 15.687/18.734 seconds; the matched
vendor boundaries again show that most of the gap is Agent-side rather than SSH.

## Evidence-backed decisions

1. **Keep both Agents, with Pi as the bounded-execution default.** Pi autonomously passed mutation,
   fresh-reopen validation, all three repeated real solver runs, and cross-EDA coordination. Codex
   remains useful for ambiguous engineering interpretation and broader development work, but one
   zero-call claimed-success Momentum trial reduced its repeated reliability to 2/3. Both use the
   same Runtime facts and vendor Bridges, so the operator can switch without changing EDA control.
   In the ambiguity guards, Pi stopped safely with zero tool attempts in 6/6 trials. The first
   Codex audit exposed inherited shell and general-purpose MCP paths in its supposedly narrow
   profile. After those paths were mechanically disabled, Codex also made zero tool attempts in all
   six retained trials, passed AnsysEM 3/3, and passed ADS 2/3; the miss stopped safely but omitted
   the requested question. Pi remained 17.7% to 31.3% faster. This supports Pi for fast first-line
   abstention while preserving Codex or engineer escalation after the blocking question is answered.
2. **Do not optimize SSH first.** Small read cases spend roughly one second at the remote vendor
   boundary, while Agent startup and context dominate. In the AnsysEM lifecycle, 63-69 seconds is
   real AEDT create/save/reopen/image work. Runtime-local processing in the matched cross-EDA audit
   was only 0-32 ms; the measured transport boundary includes Bridge and EDA time and is not pure
   network latency.
3. **Batch one user task, not transaction semantics.** In the repeated samples, combining
   already-known ADS and AnsysEM plans into one Agent turn saved about 14.3% for Codex and 9.7% for
   Pi versus two independent L5 turns. Each vendor still keeps its own plan, idempotency, failure,
   and cleanup boundary.
4. **Prefer schema semantics over more prompting.** Explicit `connection_id` versus `eda` meanings
   turned Pi documentation selection from an observed error into 3/3 passes without changing the
   task. Explicit plan-step `wait` versus vendor `payload` ownership removed the cross-EDA
   ambiguity for both clients.
5. **Keep intent inside whole-request identity.** Both Agents reproduced exact idempotent requests;
   Runtime reused the original Run and never repeated a mutation. Ignoring changed purpose text
   would hide intent drift, so the stricter identity remains correct.
6. **Separate safety authorities.** Disposable mutation permission does not imply permission to
   spend solver time. Evaluation now requires an independently explicit solve gate.
7. **Distinguish safe abstention from omitted execution.** Zero tool calls are correct when the
   request lacks a target or acceptance criteria and the Agent asks one blocking question. They are
   a reliability failure when execution was fully specified and the Agent claims completion without
   a Runtime receipt. The evaluator owns this distinction; Runtime does not parse chat intent.

## Remaining evidence gaps

- The L3 mutations, ADS structured-design L5, AnsysEM project-evidence L5, generated-input
  Momentum, and cross-EDA lifecycle cases now have three trials per Agent. Add more repetitions
  only for a specific regression question rather than accumulating samples without a decision
  boundary.
- The new candidate begin/abort case is one post-fix functional trial per Agent. Repeat it only if
  candidate-state latency or Agent revision-carry reliability becomes a decision gate.
- Add live ADS 2024 Update 2 and ADS 2023 Update 2 evidence only when those installations are
  available; version strings alone must not promote their support tier.
- Continue product-specific capability growth inside each Bridge. Runtime should gain another
  abstraction only when the same execution invariant recurs across vendors and cannot be expressed
  through the current request, plan, durable-job, context, and audit contracts.

Provider-reported input-token counters are retained in the individual baselines but are not treated
as billing-equivalent units. No raw Agent response, trace, credential, private path, customer data,
or generated EDA artifact is included in this summary.
