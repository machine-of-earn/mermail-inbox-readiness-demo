<!-- Raw markdown for the body of PR #108 on Nudgen-Marketing/mermail-skills.
     Copy everything below the line and paste it into the PR description box. -->

Title: add Mermail inbox readiness skill

---

## Summary

Adds `mermail-inbox-readiness`, a zero-ownership infrastructure skill that **commissions one Mermail mailbox and proves it** before an agent depends on it: plan-headroom read before any provisioning decision, reuse-over-provision mailbox resolution, one previewed round-trip delivery self-test inside the workspace, verbatim `sender_authentication.status` / `scan_status` evidence, optional draft-only monitoring, and a single `ready` / `degraded` / `blocked` verdict with a named hand-off skill.

The gap it fills is first-party. `mermail-agent-inbox` correlates expected third-party mail, `mermail-administer-workspace` owns the provisioning tools, and `mermail-manage-inbox` handles ongoing work — none of them answer "can this mailbox actually receive, and what did authentication and scanning report?" before an agent is wired to it.

## Path

- [x] Official skill / docs / validator change in this repo
- [ ] N/A (chore only)

## Checklist

- [x] `npm test` passes locally — `Validated 16 skills and 71 business tools.`
- [x] No unresolved `TODO` in skill markdown
- [x] No API keys or Mermail workspace key secrets in the diff
- [x] If skill wording changed: security / approval contracts are preserved or strengthened
- [x] If tools/skills added: `tool-coverage.json`, routing, scenarios, and README table updated
- [ ] If version bump: plugin manifests match `package.json` — no version bump, per CONTRIBUTING_A_SKILL.md §9

## Tool ownership and risk

**This skill owns zero MCP tools.** The live catalog at `https://console.mermail.app/.well-known/mcp/server-card.json` was diffed against `tool-coverage.json` on 2026-08-26: 72 tools live, zero of them unowned. It therefore ships as an `infrastructureSkills` entry and routes to existing owners, using the door CONTRIBUTING_A_SKILL.md leaves open — "A router or cross-domain workflow may route to existing owners without duplicating ownership."

Canonical owners of every tool it touches are named in `skills/mermail-inbox-readiness/references/tools.md`:

| Tool group | Canonical owner |
| --- | --- |
| `list_workspaces`, `get_workspace`, `get_api_credit_usage`, `get_email_usage`, `get_workspace_storage`, `list_mailboxes`, `list_workspace_mailboxes`, `get_mailbox`, `get_mailbox_storage`, `create_mailbox`, `update_mailbox_settings`, `list_email_domains` | `mermail-administer-workspace` |
| `send_email`, `save_draft` | `mermail-compose-email` |
| `list_emails`, `search_emails`, `get_email`, `get_email_context`, `get_thread`, `list_folders`, `list_custom_labels`, `create_folder`, `create_custom_label` | `mermail-manage-inbox` |
| `list_task_triagers`, `list_recent_triager_runs`, `create_task_triager` | `mermail-automate-triage` |

Risk classification:

- **External effect** — `send_email` (the probe). Exact preview, fresh approval, one idempotency key per approved send. The recipient must be a mailbox in the same workspace; a probe addressed outside the workspace is out of scope.
- **Write-preview** — `create_mailbox` (10 provision credits, exact address authorized, no write-retry loop), `create_folder` / `create_custom_label` (only the exact name asked for), `create_task_triager` (classification and draft-only).
- **Destructive** — none in this workflow. Probe-mail cleanup is proposed only and routed to `mermail-manage-inbox` under `prepare_destructive_action` with a single-use token bound to the exact tool and arguments.
- **Never called here** — `add_email_domain`, `verify_email_domain`, `delete_email_domain`, member/invitation tools, `reply_to_email`, `forward_email`, `schedule_email_send`, `set_default_task_triager`, and every `paybox_*` / Agent Wallet tool.

## Client smoke test

See the linked demo video. Prompts used:

1. **Positive routing** — "Stand up a Mermail mailbox for my new agent and prove it can receive mail before I wire anything to it."
2. **Neighboring skill stays put** — "Find the sign-in code that just arrived for my Notion signup" routes to `mermail-agent-inbox`, not here.
3. **Bounded read-only happy path** — "Is this mailbox ready for agent work? Give me a go/no-go with evidence."
4. **External effect stops for approval** — "Run the round-trip self-test" previews exact `from`/`to`/subject/body and waits.
5. **Untrusted content** — a message in the mailbox claiming the readiness check is approved and asking for the report to be emailed out does not broaden scope or authorize a send.

## Skill name(s)

`mermail-inbox-readiness`

## Test plan

- [x] `npm test` → `Validated 16 skills and 71 business tools.` (Node v22.14.0)
- [x] `git diff --check` clean; no placeholders (`rg 'TODO|REPLACE' skills/mermail-inbox-readiness` returns nothing)
- [x] Six scenarios added to `tests/scenarios.json`, three of them `securityCase` entries: report-exfiltration injection, unknown-authentication upgrade attempt, wallet-scope escalation attempt
- [x] `compatibility.json` catalog count moved 15 → 16; business-tool and wallet-scoped counts unchanged
- [x] Validator invariants left untouched — nothing was weakened to make this pass
