# onelive-integrity — the operational-integrity plugin

One versioned source of the founder's operating rules, enforced mechanically.
Lives inside the onelive repo (single source of truth, covered by every gate
this repo runs); other lanes reference it — they never copy it.

## What it does

- **SessionStart banner** (`scripts/plan_first_banner.py`): injects the
  operating rules into every session's opening context.
- **PreToolUse gate** (`scripts/plan_first_gate.py`): denies Write/Edit on
  product files until the repo's STATE file carries an OPEN Session Contract
  with the five plan fields (WHAT / HOW / WHY / WHY-IT-MATTERS / EXPECTED
  OUTCOMES). Bookkeeping files stay writable; unreadable state fails closed.
- **Charter** (`plugins/integrity/charter/OPERATING_INTEGRITY_CHARTER.md`):
  every rule the founder has directed, with sources — the canonical text.
- **Paste-in** (`plugins/integrity/charter/CLAUDE_PROJECT_PASTEIN.md`): the
  behavioral version for claude.ai Projects, where hooks cannot run.

## New-lane checklist (one settings block + one paste)

1. In the new repo's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "onelive-integrity": {
      "source": {
        "source": "github",
        "repo": "schubertsean-ui/onelive",
        "path": "integrity-plugin/.claude-plugin/marketplace.json",
        "sparsePaths": ["integrity-plugin"]
      }
    }
  },
  "enabledPlugins": {
    "integrity@onelive-integrity": true
  }
}
```

2. Optionally add `.plan-first.json` at the repo root to name a different
   state file or extra bookkeeping paths (malformed config fails closed):

```json
{ "state_file": "STATE.md", "extra_bookkeeping": ["docs/notes/"] }
```

3. For claude.ai Projects (chat — no hooks): paste
   `CLAUDE_PROJECT_PASTEIN.md` into the Project's custom instructions.

4. Verify in the first session: the `[integrity]` banner prints at start, and
   an edit to a product file without an OPEN five-field contract is denied.

## Honest limits (stated so nobody has to rediscover them)

- Hooks bind Claude Code sessions in repos that enable the plugin. Plain
  claude.ai chat gets the paste-in — instructions, not physics.
- The onelive repo itself runs local copies of these hooks
  (`.claude/settings.json` + `tools/plan_first_*.py`) so its enforcement
  never depends on marketplace resolution; the plugin mirrors them for other
  lanes. `tests/test_integrity_plugin.py` keeps the two in lockstep — drift
  fails the suite.
- The charter contains every founder correction ON THE RECORD in this repo.
  A rule harped on elsewhere but never recorded here must be added — one
  line to the charter, and it propagates to every lane.
