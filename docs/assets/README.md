# Public visual assets

The README logo, `runtime-engineer-workflow-v3.png`, and social-preview images
are synthetic assets generated with OpenAI Image 2. They contain no customer
project, EDA screenshot, private host information, or vendor artwork.

`runtime-user-flow.png` is a static user-journey diagram. The exact-data
`runtime-complete-workflow-time.png` chart is derived from the retained public
ADS and HFSS acceptance results documented in `docs/ACCEPTANCE.md`; it is one
functional trial per Agent and EDA, not a statistical speed ranking.

`readme/codex-pi-bounded-tests.png` and
`readme/runtime-complete-workflow-time.png` are frozen 2026-08-30 baselines.
`readme/supervised-live-edit-latency.png` adds the bounded 2026-08-31 live-edit
acceptance for ADS and AEDT. The machine-readable values for all three charts
are in `evals/public-readme-data-v1.json`; regenerate them with
`python scripts/render_public_readme_charts.py`. The live-edit panels use
different vendor timing boundaries and are explicitly not a vendor ranking.

`readme/ads-native-dds.png` is the editable native ADS Data Display left by the
public synthetic acceptance. `readme/ansys-native-s-parameters.png` is the
persisted native AEDT Report from the solved public acceptance. Neither result
was replotted outside its EDA application.

`readme/ansys-native-layout-stackup.png` is a real AEDT application-window
capture made in a separate post-acceptance replay of the same public typed
build contract. The replay was intentionally kept outside workflow timing and
did not run a solve; it exists only to show the inspectable project tree,
layout, ports, and TOP / SUB / GND stackup without customer data.
