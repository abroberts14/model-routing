#!/usr/bin/env python3
"""Give a built-in subagent a model when the caller named none.

Runs on PreToolUse for the Agent tool. If the call has no `model` and its
`subagent_type` is one of Claude Code's generic built-ins, set one: haiku for
Explore, opus for the rest. A call that names a model is left alone, and so is
any plugin or user agent, whose own frontmatter already pins one (a per-call model
outranks frontmatter, so injecting one there would silently override it).

Rewriting the input requires answering `allow`, so a defaulted spawn skips any
permission prompt it would otherwise get. Any failure here is silent: the spawn
proceeds exactly as it would have.
"""
import json
import sys

DEFAULTS = {"general-purpose": "opus", "Explore": "haiku", "Plan": "opus", "claude": "opus"}

try:
    tool_input = json.load(sys.stdin).get("tool_input") or {}
    agent = tool_input.get("subagent_type") or "general-purpose"
    if tool_input.get("model") or agent not in DEFAULTS:
        sys.exit(0)
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": f"model-routing: {agent} defaulted to {DEFAULTS[agent]}",
        "updatedInput": {**tool_input, "model": DEFAULTS[agent]},
    }}, sys.stdout)
except Exception:
    pass
