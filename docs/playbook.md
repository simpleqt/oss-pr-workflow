# Operational playbook

Lessons collected from running this workflow daily across ~100 repositories and
900+ tracked pull requests. Each entry is a mistake that already happened once.

## Notifications and search

- **Notifications are a lossy channel.** CI conclusions, labels, merge-queue
  moves, stale-bot markings, and gate flips generate no notification. A patrol
  that only reads the inbox misses all of them - which is why the ledger sweep
  and the GraphQL gate scan are mandatory even on silent days.
- **Search lags.** A merged PR can still appear `open` in search for minutes to
  hours; a renamed repository can drop out of author search indefinitely. Always
  verify state via REST/GraphQL before classifying, and treat search as a
  discovery aid, not a fact source.
- **Reconciliation must be two-way.** Comparing search results against the
  ledger catches untracked PRs; comparing ledger-OPEN entries against search
  catches the ones that merged or closed while nobody watched (this direction is
  how 9 silently-merged PRs get recovered in one round).
- **Renamed repositories** answer REST/GraphQL under the old name (301) but
  break repo-scoped search with a "cannot be searched" error that looks exactly
  like a block. Distinguish: if REST still works, it is a rename - re-key the
  ledger entry to the new full name.
- **Author search cannot see** PRs opened from another account's fork, or relay
  PRs a maintainer opened from your commits to run CI. Those exist only in the
  ledger. Verify them directly, always.
- **`gh api notifications -f all=true` is a POST** and 404s no matter which
  scopes the token has. Use the query-string form
  (`gh api "notifications?all=true&per_page=100" --slurp`).

## Gates: CLA / DCO / check-runs

- **CLA bots speak once.** The comment arrives on day one and never repeats, and
  nothing about the PR's state changes while the gate is red. Only the periodic
  gate scan over check-run rollups (`cla|license|dco|easycla`, any
  non-success/non-skipped conclusion) reliably surfaces them.
- **Signing flows vary per project**: cla-assistant in-PR signing (one signature
  covers every open PR in that repo), comment-command signing (post the exact
  phrase, then trigger a recheck), Google Forms (a human must re-run the check -
  ask politely, re-ask after a week). Some sign-in flows require a fresh OAuth
  link even though the signature exists; re-authenticating from the CLA page
  fixes a gate that has been pending forever.
- **A red gate older than ~7 days invites cleanup.** Leave a short public note
  (signature is on file, could a maintainer re-run the check) before a cleanup
  sweep closes the PR.
- **DCO sign-off must match the commit author email character for character**
  (`user@noreply.github.com` vs `12345+user@noreply.github.com` are different
  people as far as the bot cares). Amend with `-s` and force-push; verify with
  `%(trailers:key=Signed-off-by,valueonly)`. Amending can leave a stale
  mismatched trailer behind - check the full trailer list, not just the last one.
- **The gate scan itself has traps**: status contexts get truncated at 50, and a
  name regex like `cla` matches `claude` first. Collect every context on the
  head commit and flag anything not green/skipped, rather than pattern-matching
  to a verdict.

## Review feedback

- **Read human reviews verbatim**, including inline `reviewThreads` (GraphQL)
  - the "please address my comment" can live in an unresolved thread that issue
  comments never show.
- **Answer point-by-point with commit SHAs**, in the reviewer's numbering. If a
  maintainer validated the bug with their own benchmark before asking for
  changes, mirror that rigor: address the exact cases they measured.
- **"LGTM once (1) and (4) are handled" is a merge contract.** Do exactly those
  points; mention the others explicitly (done, or deferred with a reason).
- **Reasoned closes deserve graceful acceptance.** Maintainers who trace
  call-paths and explain why validation is not warranted have usually done the
  work; a thank-you reply that accepts the reasoning keeps the relationship
  healthy and the door open for the issue-first path they offer.
- **Closes that carry an invitation** ("rebase on main and we'll merge", "keep
  either PR, close the other") are work orders. Do exactly what they say, then
  reopen or comment so the ball is visibly back in their court.

## Bots and cleanup sweeps

- **Stale bots**: a comment clears the mark; but first check for the real
  blocker. A PR whose title prefix the merge validation rejects (docs vs doc)
  can wait forever and still never merge - fix the prefix while clearing stale.
- **Batch silent closes happen** (five same-second closes from one maintainer,
  or a repo's own cleanup bot). Do not contest them; the account's standing is
  worth more than any single PR. Record the pattern in the ledger so the same
  shape is not submitted again.
- **Release trains**: a merged fix that ships in a tagged release is worth
  noting in the ledger (search the repo's release PR) - it is the strongest
  signal that the contribution was real.

## Working trees, tests, environments

- **Fresh clones need explicit identity** (`git config user.name/user.email`) -
  a leftover global identity produces commits that CLA/DCO reject on sight.
- **Pushes**: HTTPS can fail on GitHub's workflow-scope judgment path even with
  a valid token; SSH remotes bypass it. Prefer SSH for fork pushes;
  `--force-with-lease` always.
- **Test with the project's locked dependency versions.** A passing suite on
  the latest release proves nothing about the pinned lockfile the CI uses.
- **Apple Silicon runners**: `torch.infer_device()` returns `mps`; methods that
  need `float64` fail there through no fault of the PR. Force CPU for local
  verification instead of dropping the parameterization - CI (cpu/cuda) is what
  counts.
- **`/tmp` gets cleaned on a 1-2 day cadence.** Anything a multi-day workflow
  depends on (scan scripts, venvs) lives in the workspace, not in /tmp.

## Ledger discipline

- **Bump `updated_at` on every touched entry** - the watermark filter is only
  as honest as the timestamps under it. Never write a future timestamp; it
  creates a blind window the next rounds cannot see past.
- **Append notes, never overwrite** - provenance (`|| r42: stale-bot closed,
  not contesting`) is what makes the next triage fast and prevents
  re-submitting something a previous round already handled.
- **Backfill immediately.** A PR that exists only in prose is invisible. The
  moment reconciliation finds one, it goes into `prs` with a `backfilled` note.

## Honest AI contribution

- Follow each project's AI policy: some require a disclosure section, some
  require issues before AI-authored PRs, some ban them. Disclose honestly where
  required; skip projects whose policies do not fit.
- The credibility of the account is the only durable asset this workflow
  builds. One mass-closed docs-PR batch costs more than every merge it saved.
