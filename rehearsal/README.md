# Rehearse `mermail-inbox-readiness` with no credentials

**TLDR: `mermail_mock.py` is a 183-line offline stand-in for the Mermail MCP server, so
anyone can run the skill end to end before they have an API key.** Register it as a stdio
MCP server, ask the skill to commission a mailbox, and the whole workflow — headroom read,
mailbox reuse, previewed probe, approval stop, capped poll, verdict — plays out against
fixtures instead of the live service.

It is a rehearsal harness, not a substitute. The submitted demo video was recorded against
the real server at `https://console.mermail.app/mcp`; a run against this mock proves the
*workflow*, never the service.

## Run it

```bash
# 1. register the mock (Claude Code; any MCP client that speaks stdio works the same way)
claude mcp add mermail -- python3 /path/to/rehearsal/mermail_mock.py

# 2. install the skill from the pull request branch, then ask for the workflow
"Stand up a Mermail mailbox for my new agent and prove it can receive mail."
```

No network, no key, no account. State lives in `/tmp/mermail-mock-state.json`
(override with `MERMAIL_MOCK_STATE`) so a two-turn rehearsal keeps the message it
just sent — a mailbox that forgets its own probe is instantly detectable as a fixture.

## What it answers

The 15 tools this skill routes to: `get_api_credit_usage`, `get_email_usage`,
`get_workspace_storage`, `list_workspaces`, `get_workspace`, `list_email_domains`,
`list_mailboxes`, `get_mailbox`, `create_mailbox`, `send_email`, `list_emails`,
`get_email`, `list_folders`, `list_custom_labels`, `list_task_triagers`. Response
shapes are taken from the skill's own `references/tools.md`.

## What it deliberately gets wrong

A fixture that passes everything teaches nothing. This one returns
`sender_authentication.status: "unknown"` on a domain whose SPF and DKIM both pass, so a
rehearsal has to exercise the rule the skill is built around: **`unknown` is not `pass` and
never rounds up.** A correct run ends on `degraded`, names the check that answered
`unknown`, and does not claim `ready`.

`send_email` honours the idempotency key and answers `conflict` on a replay, so the
"never send a second probe without a new approval" branch is reachable too.
`create_mailbox` refuses by design — the workflow is supposed to prefer reuse over
spending 10 provision credits.

## Not affiliated with Mermail

This file is a test double written from the public tool contracts, published here so the
demonstrated workflow is reproducible. It is not Mermail's code, it is not endorsed by
Mermail, and no output from it should ever be presented as a live result.
