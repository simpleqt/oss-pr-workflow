# oss-pr-workflow

一个 Agent 技能（外加一个小型扫描脚本），用于在大量 GitHub 仓库上运行**自动化、
带质量门禁的开源贡献工作流**：把有实质内容的修复作为 PR 提交，然后持续盯守所有已提交
的 PR —— 通知、评审反馈、CI 与 CLA/DCO 门禁、stale bot —— 直到每个 PR 要么被合并、
要么被明确拒绝。

在约 100 个仓库、约 900 个 PR 的实战中打磨成型。

## What it does

**Submission side**

- Mechanical quality gate before any PR: strip docs/comment-only hunks and
  require a real behavior change, a red/green regression test, and the
  project's pinned linters - no filler docs PRs, ever.
- Project AI-policy compliance and honest AI disclosure where required.

**Patrol side** (runs even when notifications are empty)

- Full ledger reconciliation in both directions (search -> ledger for
  backfill, ledger -> REST for silent merges/closes), so nothing drifts.
- One batched GraphQL sweep over every open PR: state, head, latest review,
  and check-run rollup - flagging any `cla|license|dco|easycla` gate that is
  not green, with the signing URL.
- Review triage: bots skimmed, human reviews read verbatim (including inline
  threads), fixes implemented in worktrees and pushed point-by-point.
- Graceful handling of reasoned closes, "rebase and we'll merge" invitations,
  and stale-bot defense.

Everything lands in a single append-friendly JSON ledger
(`pr-watch-state.json`) with a watermark, merge log, and pending user actions.

## Repository layout

```
skills/oss-pr-workflow/SKILL.md   the skill itself (agent-facing SOP)
docs/playbook.md                  distilled operational lessons (the why)
scripts/sweep_scan.py             batched GraphQL liveness+gate scanner
examples/pr-watch-state.example.json
```

## Install

Copy the skill directory into your agent's skill location:

```bash
git clone https://github.com/simpleqt/oss-pr-workflow.git
mkdir -p ~/.claude/skills   # or your agent's equivalent skills directory
cp -r oss-pr-workflow/skills/oss-pr-workflow ~/.claude/skills/
```

Requirements: the [GitHub CLI](https://cli.github.com/) (`gh`) authenticated as
the contributing account, and Python 3.10+ for the sweep script.

## Usage

In an agent session with the skill installed:

- "检查最新消息" / "check my PR messages" -> runs the full patrol loop.
- "Patrol and don't miss anything" -> the loop plus an explicit liveness sweep
  and gate scan over all open PRs.
- "Fix the review comments on PR #123" -> worktree fix, red/green test,
  lint, push, point-by-point reply.

Standalone (no agent needed), sweep every open PR for state + gate health:

```bash
gh search prs --author=YOUR_ACCOUNT --state=open --limit 1000 \
  --json repository,number > /tmp/prs_open.json
python3 scripts/sweep_scan.py /tmp/sweep_out.json
```

## The ledger

`examples/pr-watch-state.example.json` documents the schema:

- `updated_at` - the notification watermark; also bumped per touched PR.
- `prs` - every PR the account owns: state, timestamp, and an append-only
  provenance note per patrol round.
- `merged_log` / `total_merged_confirmed` - confirmed merges (the only
  merge count that matters for reporting).
- `user_actions_pending` - things only the human can do (CLA forms, 2FA
  confirmations), each with its URL.

## License

[MIT](LICENSE)
