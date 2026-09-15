# model-routing

A small Claude Code plugin that keeps the expensive model for decisions and puts
everything else on a cheaper one.

Three pieces:

- **Four agents**, each pinned to the cheapest model that does its job. `architect`
  on Fable, for one decision at a time. `worker` and `reviewer` on Sonnet. `editor`
  on Haiku at low effort.
- **One hook** that gives a model to any built-in subagent spawned without one:
  Haiku for `Explore`, Sonnet for `general-purpose`, `Plan`, and `claude`. Without
  it those spawns inherit the session's model, so delegating from a Fable or Opus
  session buys you a Fable or Opus worker.
- **A routing note**, [`ROUTING.md`](ROUTING.md), attached to the start of every
  session. Do ordinary work here. Reach up to `architect` for four kinds of decision,
  with a brief rather than the conversation. If the session is itself on Opus or
  Fable, decide here and hand execution down. Name a model on every spawn.

Nothing is locked. `/model fable` still works, and every agent's model is one line
in one file.

## Install

Claude Code loads any directory under `~/.claude/skills/` that has a
`.claude-plugin/plugin.json` as a plugin. No marketplace, no install step, and it
reads the directory in place.

```bash
git clone https://github.com/abroberts14/model-routing ~/.claude/skills/model-routing
```

It loads on the next session as `model-routing@skills-dir`, or right away with
`/reload-plugins`.

To try it for one session without installing:

```bash
claude --plugin-dir /path/to/model-routing
```

Also set these in `~/.claude/settings.json`. `model` makes Sonnet the session
default, which the routing note assumes. `autoCompactWindow` caps how much history
each step re-reads. The other two keep long command and MCP output out of the
history in the first place.

```json
{
  "model": "sonnet",
  "autoCompactWindow": 200000,
  "bashOutputMaxChars": 15000,
  "env": { "MAX_MCP_OUTPUT_TOKENS": "10000" }
}
```

Built and tested on Claude Code 2.1.272. `bashOutputMaxChars` needs 2.1.261 or later.

## Agents

| Agent | Model | Use it for |
| --- | --- | --- |
| `architect` | Fable | One decision where being wrong is expensive: an approach that spans systems or changes a data model, a bug that survived two fixes, anything touching auth, isolation, payments, or production data, a long-lived tradeoff. Gets a brief, returns a decision and a step plan. Never implements. |
| `worker` | Sonnet | The default. A scoped piece of work once the direction is settled: a bounded code change, tests for existing behaviour, a config change, a doc. Finishes it, runs it, reports what it verified and what it assumed. |
| `reviewer` | Sonnet | Work you did not do. Two questions: is it wrong, and is it finished. Findings with file and line, plus a per-item done list. Reports, never fixes. |
| `editor` | Haiku, low effort | Mechanical edits with zero design decisions: renames, version bumps, moving files, applying a given diff, lint fixes. |

Each agent's description is always-on context in every session. For these four
that is about 600 tokens; `claude plugin details model-routing@skills-dir` shows
the current figure.

## The hook

[`hooks/default-subagent-model.py`](hooks/default-subagent-model.py) runs before
every Agent tool call. If the call names no model and the subagent type is one of
Claude Code's generic built-ins, it adds one and returns the rewritten call. It
never overrides a model named on the call (sessions do that on their own more often
than you would think), and it never touches a plugin or user agent, whose own
frontmatter already pins one.

One tradeoff. A hook that rewrites a tool call's input has to answer the permission
question itself, `allow` or `ask`. `ask` would prompt on every defaulted spawn, so
this hook answers `allow`, which means a defaulted spawn skips any permission prompt
it would otherwise get. For a personal setup that is fine.

### Do you need the hook, or just `CLAUDE_CODE_SUBAGENT_MODEL`?

Since Claude Code 2.1.251 that variable is a fallback, below a model named on the
call and below an agent's own frontmatter, so it no longer demotes pinned agents.
It covers `general-purpose` and `claude`. It does not cover the built-in `Explore`
and `Plan`, which inherit the session's model (capped at Opus). Measured on 2.1.272
from an Opus session, spawning both with no model on the call:

| Setup | `Explore` ran on | `general-purpose` ran on |
| --- | --- | --- |
| `CLAUDE_CODE_SUBAGENT_MODEL=haiku`, no hook | Opus | Haiku |
| No variable, this plugin loaded | Haiku | Sonnet |

So if you do not care about `Explore` and `Plan`, set the variable to `sonnet` in
the `env` block of your settings and delete the PreToolUse entry from
`hooks/hooks.json`. The hook stays on by default here because `Explore` is the
spawn that happens most, and from a Fable or Opus session it runs on Opus.

`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` overrides everything, including `architect`,
so leave that unset.

## The routing note

A SessionStart hook prints `ROUTING.md` into context, because a plugin cannot ship
a `CLAUDE.md`. Project-specific rules go in the project's own `CLAUDE.md`. If you
would rather not run the hook, paste the note into `~/.claude/CLAUDE.md` and delete
the SessionStart entry from `hooks/hooks.json`.

## Changing it

Edit the file, then `/reload-plugins`. Agents and hooks are read from the directory
in place, so there is no version to bump and nothing to reinstall.

## Checking it

```bash
claude plugin list
claude plugin details model-routing@skills-dir
```

Before installing, the same inventory from a checkout:

```bash
claude --plugin-dir /path/to/model-routing plugin details model-routing
```

That proves the plugin loaded. To see which models your sessions actually ran on,
count them in the local transcripts. Subagent transcripts sit in a `subagents/`
folder beside each session file, so the second command counts workers only.

```bash
grep -rhoE '"model":"claude-[^"]+"' ~/.claude/projects --include='*.jsonl' | sort | uniq -c | sort -rn
find ~/.claude/projects -path '*/subagents/*.jsonl' -exec grep -hoE '"model":"claude-[^"]+"' {} + | sort | uniq -c | sort -rn
```

If Fable or Opus keeps showing up in the second count after install, a subagent is
inheriting it from the main session and the hook is not taking effect.

## What is enforced and what is only words

| Piece | Enforced? |
| --- | --- |
| An agent's `model:` | Yes, by Claude Code. The one override is a model named on the call itself. |
| The default for unnamed built-in spawns | Yes. The hook rewrites the call before it runs. |
| The routing note | No. It is text the session reads. It shapes behaviour; it does not bind it. |
| `model: sonnet` in settings | A default, not a lock. |

## License

MIT.
