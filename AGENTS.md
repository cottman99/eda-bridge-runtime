# Agent working agreement

- Treat this as a public repository. Never add customer data, credentials,
  private hostnames, private paths, or proprietary EDA models.
- Preserve the agent-neutral and vendor-neutral boundary.
- Every operation initiated by an agent must include a concise `purpose`.
- Prefer typed capabilities over arbitrary script execution.
- Keep local and SSH behavior conformant through shared tests.
- Do not claim success until durable state or a fresh observation proves it.
- Do not publish or create releases without explicit owner authorization.

## User-facing release communication

- Write README and GitHub Release content for engineers who want to complete
  EDA work, not primarily for maintainers or API developers.
- Lead with the user outcome, then native application evidence and exact
  observed results. Put architecture, PRs, commits, and implementation detail
  later.
- Keep validation runs clean. Do not add screenshots, camera work, plots, or
  promotional steps to a timed engineering acceptance.
- After a successful run is frozen, promotional material may be made by
  replaying or reopening that exact accepted result. Record this separately as
  release preparation, never as engineering-task time.
- Use real vendor-application windows and native editable results when they
  exist. Do not substitute mockups or external replots for native evidence.
- Describe only outcomes supported by the accepted example, but do not turn the
  release page into defensive language. Put planned expansion in a short,
  positive Roadmap or Next section.
- Keep installation short and task-oriented. Put compatibility detail,
  changelogs, PRs, checksums, and developer notes at the end or behind links.
- Follow `docs/USER_FACING_RELEASES.md` when editing a README, release note,
  public example, or homepage visual.
