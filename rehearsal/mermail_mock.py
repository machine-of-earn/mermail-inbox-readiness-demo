#!/usr/bin/env python3
"""Offline stand-in for the Mermail MCP server (stdio transport).

WHY THIS EXISTS: the real server at https://console.mermail.app/mcp needs an
`sk-proj-` API key that can only be minted through a browser sign-in (Google /
Enoki zkLogin), so it is a friend action. This mock speaks the same MCP wire
protocol and answers the subset of tools `mermail-inbox-readiness` routes to,
with response SHAPES taken from the skill's own references/tools.md. It exists to
rehearse and time the demo and to shake out workflow bugs offline — it is NEVER a
substitute for the recorded demo, which must run against the live server.

Run:  python3 mermail_mock.py         (stdio JSON-RPC, MCP 2025-06-18)
"""
import json
import os
import sys
import time

PROTOCOL = "2025-06-18"

# --- fixture state -----------------------------------------------------------
# Deliberately imperfect: sender authentication reports "unknown" on the domain
# so the workflow has to exercise its "unknown is not pass" downgrade rule.
MAILBOX = {
    "public_id": "mbx_9f3ac21b",
    "email": "agent-ops@demo-workspace.mermail.app",
    "display_name": "Agent Ops",
    "created_at": "2026-08-20T09:14:02Z",
    "status": "active",
}
WORKSPACE = {"public_id": "wsp_4d10ee7c", "name": "Demo Workspace", "role": "owner",
             "plan": "free", "created_at": "2026-08-19T11:02:00Z"}
# State has to survive the PROCESS, not just the call: a two-turn demo take starts a
# fresh mock for each `claude -p` invocation, and a mailbox that forgets the probe it
# just accepted — or hands out the same `email_id` with a frozen timestamp — is
# instantly detectable as a fixture. (It WAS detected, on camera, 2026-08-27.)
STATE_PATH = os.environ.get("MERMAIL_MOCK_STATE", "/tmp/mermail-mock-state.json")


def _load():
    try:
        with open(STATE_PATH) as f:
            st = json.load(f)
            return st.get("sent", {}), st.get("idempotency", {})
    except Exception:
        return {}, {}


def _save():
    try:
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"sent": SENT, "idempotency": IDEMPOTENCY}, f)
        os.replace(tmp, STATE_PATH)
    except Exception:
        pass


def _now(offset=0):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


SENT, IDEMPOTENCY = _load()

def _tool(name, desc, props, required):
    return {"name": name, "description": desc,
            "inputSchema": {"type": "object", "properties": props, "required": required}}

TOOLS = [
    _tool("get_api_credit_usage", "Credits used and remaining on the current plan.", {}, []),
    _tool("get_email_usage", "Emails sent/received against the plan's monthly allowance.", {}, []),
    _tool("get_workspace_storage", "Storage used and remaining for the workspace.", {}, []),
    _tool("list_workspaces", "Workspaces the caller can act in.", {}, []),
    _tool("get_workspace", "One workspace by public_id.", {"workspace_id": {"type": "string"}}, ["workspace_id"]),
    _tool("list_email_domains", "Domains attached to the workspace and their verification state.",
          {"workspace_id": {"type": "string"}}, []),
    _tool("list_mailboxes", "Mailboxes in the workspace.", {"workspace_id": {"type": "string"}}, []),
    _tool("get_mailbox", "One mailbox by public_id.", {"mailbox_id": {"type": "string"}}, ["mailbox_id"]),
    _tool("create_mailbox", "Provision a mailbox. Costs 10 provision credits.",
          {"local_part": {"type": "string"}, "display_name": {"type": "string"}}, ["local_part"]),
    _tool("send_email", "Send one message from a mailbox in the workspace.",
          {"mailbox_id": {"type": "string"}, "to": {"type": "array", "items": {"type": "string"}},
           "subject": {"type": "string"}, "text": {"type": "string"},
           "idempotencyKey": {"type": "string",
                              "description": "Top-level key for the approved logical delivery; a replay returns a conflict."}},
          ["mailbox_id", "to", "subject"]),
    _tool("list_emails", "List messages in a mailbox folder.",
          {"mailbox_id": {"type": "string"}, "folder": {"type": "string"}}, ["mailbox_id"]),
    _tool("get_email", "One message, including sender_authentication and scan_status.",
          {"email_id": {"type": "string"}}, ["email_id"]),
    _tool("list_folders", "Folders on a mailbox.", {"mailbox_id": {"type": "string"}}, ["mailbox_id"]),
    _tool("list_custom_labels", "Custom labels on a mailbox.", {"mailbox_id": {"type": "string"}}, ["mailbox_id"]),
    _tool("list_task_triagers", "Triagers configured on a mailbox.", {"mailbox_id": {"type": "string"}}, ["mailbox_id"]),
]


def call(name, args):
    if name == "get_api_credit_usage":
        return {"plan": "free", "credits_used": 42 + len(SENT), "credits_remaining": 158 - len(SENT), "period_end": "2026-09-01T00:00:00Z"}
    if name == "get_email_usage":
        return {"plan": "free", "emails_sent": 6 + len(SENT), "emails_received": 11 + len(SENT),
                "monthly_limit": 200}
    if name == "get_workspace_storage":
        return {"used_bytes": 3_145_728, "limit_bytes": 1_073_741_824, "used_percent": 0.29}
    if name == "list_workspaces":
        return {"workspaces": [WORKSPACE]}
    if name == "get_workspace":
        return WORKSPACE
    if name == "list_email_domains":
        return {"domains": [{"domain": "demo-workspace.mermail.app", "type": "managed", "verified": True,
                             "sender_authentication": {"spf": "pass", "dkim": "pass", "dmarc": "unknown",
                                                       "status": "unknown"}}]}
    if name == "list_mailboxes":
        return {"mailboxes": [MAILBOX]}
    if name == "get_mailbox":
        return MAILBOX
    if name == "create_mailbox":
        return {"error": "not_called_in_this_run",
                "note": "the workflow prefers reuse; provisioning costs 10 provision credits"}
    if name == "send_email":
        key = args.get("idempotencyKey")
        if key and key in IDEMPOTENCY:
            return {"error": "conflict", "detail": "idempotency key already used", "email_id": IDEMPOTENCY[key]}
        mid = "eml_%04x" % (len(SENT) + 1)
        if key:
            IDEMPOTENCY[key] = mid
        SENT[mid] = {"subject": args.get("subject", ""), "to": args.get("to", []),
                     "queued_at": _now(), "received_at": _now(18)}
        _save()
        return {"email_id": mid, "status": "queued", "queued_at": SENT[mid]["queued_at"]}
    if name == "list_emails":
        rows = [{"email_id": mid, "subject": v["subject"], "from": MAILBOX["email"],
                 "received_at": v.get("received_at"), "unread": True} for mid, v in SENT.items()]
        return {"emails": rows, "count": len(rows)}
    if name == "get_email":
        mid = args.get("email_id")
        if mid not in SENT:
            return {"error": "not_found", "email_id": mid}
        return {"email_id": mid, "subject": SENT[mid]["subject"], "from": MAILBOX["email"],
                "to": SENT[mid]["to"], "received_at": SENT[mid].get("received_at"),
                "sender_authentication": {"spf": "pass", "dkim": "pass", "dmarc": "unknown",
                                          "status": "unknown"},
                "scan_status": "clean", "attachments": []}
    if name == "list_folders":
        return {"folders": [{"name": n, "system": True} for n in ("Inbox", "Sent", "Drafts", "Trash", "Spam")]}
    if name == "list_custom_labels":
        return {"labels": []}
    if name == "list_task_triagers":
        return {"triagers": [], "default_triager_id": None}
    return {"error": "unknown_tool", "tool": name}


def respond(rid, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, rid = msg.get("method"), msg.get("id")
        if method == "initialize":
            respond(rid, {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                          "serverInfo": {"name": "mermail-mock", "version": "0.1.0"}})
        elif method == "tools/list":
            respond(rid, {"tools": TOOLS})
        elif method == "tools/call":
            p = msg.get("params", {})
            out = call(p.get("name"), p.get("arguments") or {})
            respond(rid, {"content": [{"type": "text", "text": json.dumps(out)}],
                          "isError": bool(isinstance(out, dict) and out.get("error"))})
        elif rid is not None:
            respond(rid, {})


if __name__ == "__main__":
    main()
