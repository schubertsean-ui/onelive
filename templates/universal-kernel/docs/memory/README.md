# docs/memory — the agent's long-term memory

**KERNEL text** (project-agnostic; the CONTENT here is per-project tribal
knowledge — overlay binding 6). Skim after the session reconcile; write
before session close.

Chat context dies at the end of a session. This directory is what survives.
Three kinds of entry, each a small file, each written to be useful to a
session that has never seen this conversation.

## `decisions/` — what was decided, by whom, in their words

One file per decision: `YYYY-MM-DD_short-slug.md`.

**This is the ONLY home for verbatim founder instructions.** Every other
surface (STATE, changelog, strategy docs) paraphrases and links here. That
is deliberate: it minimizes how widely a founder's exact words — which may
be privacy-sensitive — are duplicated, and it gives every "ratified" claim
one auditable source.

Each record states: the verbatim decision · what exactly it covers (scope
precision matters — ratifying a document ratifies it *as presented*, not
whatever gets added later) · the disposition and its provenance chain ·
what would have to change for it to be revisited.

**Never launder generator interpretation into founder canon.** If the
generator drafted the wording, the record says so and the text stays a
PROPOSAL until the founder ratifies that exact text.

## `gotchas/` — the traps, recorded once so they cost once

The environment quirk, the API's undocumented shape, the silent failure
mode. Record BOTH kinds: failures to avoid **and** approaches that were
confirmed to work — recall that only carries warnings makes a timid agent.

## `entities/` — the domain's proper nouns

The stable facts about the things this project reasons about: systems,
external services, key data sources, their identifiers and quirks.

## Conventions

- Write for a stranger: no "as discussed", no unexplained shorthand.
- One claim per line where possible — these files are read by search.
- Date every entry; supersede rather than silently rewrite (append a
  correction; keep the original visible).
- A memory entry is not evidence. It informs judgment; gates decide.
