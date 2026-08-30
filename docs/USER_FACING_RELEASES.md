# User-facing release communication

This is the shared content contract for EDA Bridge Runtime and vendor Agent
Bridges. It is intentionally small and may evolve as stronger public examples
are accepted.

## Audience and purpose

Write first for an engineer deciding whether the product can help finish a real
task. A release page is not primarily a changelog, architecture note, test
report, or defense of unimplemented scope.

The reader should be able to answer these questions in order:

1. What task can this release help me finish?
2. What real EDA result shows that it works?
3. What exact observed facts make the result credible?
4. What can I ask the Agent, and how do I start?
5. What useful direction comes next?

## Evidence and timing

- Keep engineering acceptance focused on the engineering task. Do not add
  promotional screenshots, viewport adjustment, decorative plots, or release
  writing to the timed run.
- Freeze the successful result and its necessary acceptance evidence first.
- Prepare public material later by reopening or replaying the exact accepted
  result without changing its engineering meaning.
- Record replay, screenshot, editing, and publication work as release
  preparation. Never include it in Agent, Bridge, EDA, solve, or complete-task
  timing.
- A public claim must remain traceable to accepted native state, numeric data,
  a persisted artifact, or a fresh observation.
- Use a real vendor-application window and native editable result when
  available. Do not replace native DDS or AEDT reports with external replots.
- Crop to the application window and choose a view that exposes the relevant
  circuit, model, setup, port, result, or project tree. Do not publish an
  uninformative full desktop.
- Remove credentials, private hostnames, personal paths, customer data, and
  other sensitive identifiers. Do not cosmetically rewrite harmless synthetic
  engineering data merely to make it look cleaner.

## Information order

Use this default order for a substantial GitHub Release or README example:

1. **Outcome title** — name the engineering result before the version number.
2. **One-sentence value** — state what the Agent can now help the user finish.
3. **Native result** — show the most informative real application capture.
4. **Completed work** — list the user-visible engineering actions.
5. **Observed results** — give concise counts, frequencies, rows, artifacts,
   or timings that were actually observed.
6. **Example requests** — provide one to three natural-language messages a
   user could send.
7. **Quick start** — provide the shortest supported path.
8. **Next** — list a few positive roadmap items when useful.
9. **Release detail** — place compatibility, upgrade notes, changelog, PRs,
   commits, assets, and checksums last.

Small corrective releases may use a shorter form, but should still lead with
the user-visible change rather than an implementation noun.

## Language

Prefer:

- “Build a circuit, run the simulation, and leave an editable native DDS page.”
- “Solved five explicit frequencies and exported finite S-parameter data.”
- “Ask: ‘Use my selected design, update the sweep, and refresh the report.’”

Avoid leading with:

- internal class, schema, transport, or adapter names;
- a raw PR or commit list;
- defensive inventories of everything not yet demonstrated;
- universal claims inferred from one bounded example.

Accuracy comes from precise positive wording and real evidence. When a future
capability is useful to mention, put it under **Next** or **Roadmap** instead of
framing the release around limitations. Retain only brief warnings that affect
data safety, compatibility, licensing, or the user's decision to run the tool.

## Product emphasis

- **ADS Agent Bridge:** lead with circuits or testbenches, simulation, numeric
  results, native DDS, layout, or EM work that the accepted example completed.
- **AnsysEM Agent Bridge:** lead with the model, stackup, ports, setup, solve,
  extracted data, and native AEDT result that the accepted example completed.
- **EDA Bridge Runtime:** lead with reliable completion across local or remote
  hosts, reconnects, Agents, and vendor tools. Show the resulting EDA work and
  concise execution evidence; do not make architecture the hero.

Brand and layout may be shared, but the engineering task remains the main
subject on each vendor page.

## Release review

Before publishing, confirm:

- the first screen communicates a user outcome without requiring architecture
  knowledge;
- every result image comes from the stated accepted example;
- exact numbers match retained evidence;
- test and release-preparation time are not mixed;
- natural-language request examples are present when helpful;
- roadmap language is positive and compact;
- developer and packaging detail follows the user story;
- links and images render on the real GitHub README or Release page.
