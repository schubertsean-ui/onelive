"""Meta (Instagram/Facebook) carousel engine.

Greppable summary: agent-driven carousel generation + learning over
published canonical events. Spec: docs/strategy/ONE_LIVE_META_CAROUSEL_ENGINE_v1.md.
Module map: config (format physics + factor space) · tiers (volume-tiered
portfolio) · generator (draft assembly, verbatim facts only) · bandit
(Thompson-sampling learner) · metrics (ledger + improvement ratchet) ·
geo (SEO/GEO discovery bundle) · autonomy (founder ratification record) ·
publish_gate (human-custody release; the ONLY path out) · agent_loop
(the autonomous cycle — structurally cannot import publish_gate).

This __init__ deliberately imports nothing: the separation between the
autonomous loop and the publish path must stay visible in each module's
own import block, where the import-guard test reads it.
"""
