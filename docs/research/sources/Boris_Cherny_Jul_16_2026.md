#   
++[Boris Cherny](mailto:boris@anthropic.com)++ Jul 16, 2026  
  

| Step & your role | Agents | What it looks like | What’s the bottleneck | Products that help with each step | Guardrails |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0: Gated | 0 | Only older or lighter/faster models are approved, latency compounds through AI gateways and custom auth, no MCP governance, internal access to AI tools is gated or process-heavy.

No IT infra or approval path for hosting Claude-created code or artifacts; outputs only exist locally. | Legacy security and approval processes, focuses on cost-per-token containment vs. outcomes, lack of true technical voices in decisionmaking. | - Claude.ai chat | - SSO/SCIM plus role-based access
- Org-level budget caps
- Deploy inside existing approvals/IAM
- Data governance package |
| How to get from step 0 to 1: Executive/buyer alignment and escalation of blockers; frameworks for launching Claude securely |  |  |  |  |  |
| 1: Assisted
You + an agent (a pair) | ~1 | One engineer, one agent, mostly supervised—a fast pair programmer. You run one session at a time and review almost every change before it merges.  Unlock: A change that used to fill an afternoon becomes something you finish between meetings. | Your attention and the need to inspect each response and code edit. Due to low trust for the model’s output and lack of self-verification, you feel you must read everything, so you never look away.

Work is synchronous: you sit and watch while Claude works, rather than moving on to the next task. | - Claude Code in the Desktop, CLI, or IDE
- Claude Cowork, Claude Design
- Usage via Anthropic API, Bedrock, Vertex, or Microsoft Foundry
- Claude Code analytics dashboard + Analytics API
- Compliance API for Claude Enterprise
- Plan mode to review intent before edits | - Per-seat spend caps
- Centrally managed model/effort settings
- Centrally managed policy
- OpenTelemetry export into existing SIEM/observability stack |
| How to get from step 1 to 2: Run more than one agent at a time; a self-verification loop you trust (tests + build + lint + e2e testing with a real dev environment); auto mode, to avoid blocking permission prompts; automate code review |  |  |  |  |  |
| 2: Parallel
Orchestrator | ~10 | One engineer orchestrates 5–10 agents at once, each on its own worktree or git checkout, jumping between them. Claude checks its own work—tests, build, lint, security scan—before you see it. Auto mode is always on. Automated code review and security review are on by default. Output multiplies, you review final diffs rather than keystrokes, and your backlog of maintenance work starts shrinking. Claude writes most of the code. 
Unlock: A backlog that used to take the team weeks becomes one engineer's afternoon of orchestration. | Reviewing output. You’re hand-writing less code and instead checking six streams of it, and this takes up more of your time.

Prompting and steering the model as you juggle sessions. | - Auto mode
- Agent view
- Claude Code Review
- Claude Security Review - Claude Code on Mobile, cloud execution in Desktop
- Usage via Claude Teams or Claude Enterprise - Claude Tag (do a single task)
- Worktree isolation in CLI and Desktop
- Remote control, so you can monitor your agents from your phone | - Analytics to monitor team usage - Automatic code quality enforcement: lint, automated tests, typecheck
- Claude powered end-to-end verification (eg. using the Claude Chrome extension or iOS/Android simulator MCP)
- Manual code review, code merge, and security review. Hold the same quality bar for human and agent-generated code
- Pre-approve common safe bash and MCP commands in settings.json |
| How to get from step 2 to 3: Give Claude a way to pull in context (let Claude read code, wikis, discussions); agency and code review speed (agents may touch code owned by other teams); break up your work into loops and routines; let Claude kick off Claude |  |  |  |  |  |
| 3: Supervised autonomy
Manager of managers (an org tree) | ~100 | Claude writes all or nearly all of the code. “Did you read the code?” becomes “what context was the model missing and how do we solve it for next time?”

Unlock: Claude proactively does work that you would have had to kick off manually before. Maintenance and cleanup that used to wait for someone to find the time now runs continuously in the background. | Trust in the loop and your team’s decision throughput. The agent tree is too deep to babysit and your trap is scaling agent count before the loop has earned widespread trust.

Ensuring tokens are used efficiently as usage increases. Requires monitoring (via OTel or Analytics) and a culture that encourages experimentation while controlling costs once internal use cases find PMF. Ask yourself: is this something an engineer would have done? | - Subagents with worktree isolation (so parallel agents don’t collide)
- Routines, /loop, /batch, and /goal to fan out repetitive work
- Dynamic workflows
- Claude Tag (have it monitor a channel or data source and kick off tasks proactively) | - Automatic code review
- Automatic security review
- Agent sandboxing
- CLAUDE.md and Skills to encode standards
- Tune Auto mode classifier based on your team’s usage
- Manage token use with model selection, advisors, LSPs, breaking up CLAUDE.md into lazy Skills |
| How to get from step 3 to 4: Scaled automation of domain-specific use cases (eg. code migration, fuzzing, feature-building, feedback remediation) |  |  |  |  |  |
| 4: AI-native
VP steering by intent | ~1,000+ | The loop is fully closed and most agents are kicked off by Claude. Hundreds to thousands of agents run; you steer by intent and monitor by exception. 

Unlock: The quarter-long migration becomes a workflow you kick off and check on. | Identifying and automating work at scale, and enforcing the right guardrails for each type of work. | - Claude Agent SDK to programmatically build and schedule agents
- Claude Tag (active in most Slack channels, auto-responding to posts) | - Cost controls for automation
- Model selection for automation |
  
  
Update — July 19, 2026: @ClaudeDevs extended Claude Code weekly limits 50% higher through August 19 — relevant for Step 2–3 parallel agent adoption where quota is the bottleneck. Not permanent. July 18 retention guide  
  
Update — July 17, 2026: Kr$na's viral final 10% dev cycle chart — 5-minute idea, 2-hour demo, 6-month polish — maps Step 1–2 (fast yellow demos) vs Step 3+ (red-bar verification in the background).  
  
On July 16, 2026, Boris Cherny — creator of Claude Code — published Steps of AI Adoption on Anthropic's site. Lance Martin reposted it July 17; the thread hit 251K+ views in hours. Cherny's thesis: he talks to engineers daily who see one person 10× output while the rest of the org stays gated — and the gap is not "more tokens," it is bottlenecks and guardrails per maturity step.  
  
Cherny mapped five steps (0–4): from legacy approval gates with zero agents to AI-native intent steering with 1,000+ agents where Claude kicks off most loops. Anthropic says it operates at Step 3; Cherny claims he personally hit Step 4.  
  
This post translates Cherny's framework into a builder checklist — with product names, bottlenecks, and links to explainx.ai's loop engineering and Claude Code loops guide corpus.  
  
FOR DEVELOPERS  
3.5K READERS  
The AI developer stack — weekly  
  
New skills, MCP servers, agent loops, and Claude Code workflows — curated for engineers building with AI. Delivered every week.  
  
Email for explainx.ai newsletterSUBSCRIBE  
TL;DR — the five steps at a glance  
  
STEP NAME YOUR ROLE ~AGENTS UNLOCK MAIN BOTTLENECK  
0 Gated — 0 — Legacy security, cost-per-token mindset, no approval path  
1 Assisted You + agent (pair) ~1 Afternoon task → between meetings Your attention; must read every edit  
2 Parallel Orchestrator ~10 Team-week backlog → one afternoon Reviewing many streams; steering prompts  
3 Supervised autonomy Manager of managers ~100 Background maintenance runs continuously Trust + decision throughput; token efficiency  
4 AI-native VP steering by intent 1,000+ Quarter migration → kickoff + monitor Automating work at scale; per-task guardrails  
Cherny on X: "There's no one right path through the steps… at each step, tokens aren't enough… you need to find and break down the next set of bottlenecks, and build up the next set of guardrails."  
  
Step 0 — Gated (zero agents)  
  
What it looks like: Only older or lighter/faster models are approved. Latency stacks through AI gateways and custom auth. No MCP governance. Internal access to AI tools is gated or process-heavy. Claude-generated code or artifacts have no IT path to host — outputs stay local only.  
  
Bottleneck: Legacy security and approval processes; orgs optimize cost-per-token containment instead of outcomes; lack of technical voices in procurement decisions.  
  
Products Cherny lists:  
  
Claude.ai chat (not full agent stack)  
SSO/SCIM + role-based access  
Org-level budget caps  
Deploy inside existing approvals / IAM  
Data governance package  
How to reach Step 1: Executive or buyer alignment, escalating blockers, and frameworks for launching Claude securely — not buying more seats.  
  
For enterprises still here after Fable export controls, Step 0 often means region-locked chat while engineering pilots Claude Code on personal machines. That mismatch is exactly what Cherny describes when one engineer 10×'s and the org chart says "not approved."  
  
Step 1 — Assisted (~1 agent, supervised pair)  
  
What it looks like: One engineer, one agent — a fast pair programmer. You run one session at a time and review almost every change before merge.  
  
Unlock: A change that used to fill an afternoon becomes something you finish between meetings.  
  
Bottleneck: Your attention and low trust. Without a self-verification loop you believe you must read everything — work stays synchronous: you watch Claude work instead of starting the next task.  
  
Products:  
  
Claude Code (Desktop, CLI, IDE)  
Claude Cowork, Claude Design  
API via Anthropic, Bedrock, Vertex, or Microsoft Foundry  
Claude Code analytics dashboard + Analytics API  
Compliance API (Enterprise)  
Plan mode — review intent before edits  
Per-seat spend caps, centrally managed model/effort settings and policy  
OpenTelemetry export into SIEM/observability  
Guardrails: Plan mode, spend caps, centralized policy, OTel into existing stacks.  
  
How to reach Step 2:  
  
Run more than one agent at a time  
Build a self-verification loop you trust — tests, build, lint, e2e in a real dev environment  
Enable auto mode to avoid blocking permission prompts  
Automate code review  
Pair with Claude Code model vs effort — Step 1 teams often burn tokens on max effort while still reviewing every line manually.  
  
Step 2 — Parallel (~10 agents, orchestrator)  
  
What it looks like: One engineer orchestrates 5–10 agents on separate worktrees or git checkouts, jumping between sessions. Claude checks its own work — tests, build, lint, security scan — before you see diffs. Auto mode always on. Automated code review and security review default on. Claude writes most of the code; you review final diffs, not keystrokes. Maintenance backlogs start shrinking.  
  
Unlock: A backlog that used to take the team weeks becomes one engineer's afternoon of orchestration.  
  
Bottleneck: Reviewing output — six streams of diffs instead of one. Prompting and steering as you juggle sessions.  
  
Products:  
  
Auto mode  
Agent view (CLI + Desktop)  
Claude Code Review  
Claude Security Review  
Claude Code on Mobile, cloud execution in Desktop  
Claude Teams / Enterprise  
Claude Tag (single task)  
Worktree isolation (CLI + Desktop)  
Remote control — monitor agents from phone  
Analytics for team usage  
Automatic lint, tests, typecheck  
Claude-powered e2e verification (Chrome extension, iOS/Android simulator MCP)  
Guardrails: Manual merge still required; same quality bar for human and agent code; pre-approve safe bash and MCP commands in settings.json.  
  
How to reach Step 3:  
  
Give Claude context pull — code, wikis, discussions  
Fix agency + code review speed when agents touch other teams' code  
Break work into loops and routines — see loop engineering guide and official /goal, /loop, /schedule taxonomy  
Let Claude kick off Claude — subagent fan-out  
This is where explainx.ai's should developers stop reviewing AI code? debate lands: Step 2 still reviews, but the unit of review shifts from tokens typed to harness output.  
  
Step 3 — Supervised autonomy (~100 agents, org tree)  
  
What it looks like: Claude writes all or nearly all code. "Did you read the code?" becomes "what context was the model missing and how do we fix it next time?" Proactive maintenance runs in the background — cleanup that waited for someone with time now runs continuously.  
  
Unlock: Work you would have kicked off manually now starts proactively.  
  
Bottleneck: Trust in the loop and team decision throughput. The agent tree is too deep to babysit — scaling agent count before the loop earns widespread trust is the trap. Token efficiency at scale requires OTel or Analytics and a culture that experiments then controls cost after PMF.  
  
Cherny's test: "Is this something an engineer would have done?"  
  
Products:  
  
Subagents + worktree isolation  
Routines, /loop, /batch, /goal  
Dynamic workflows — see dynamic workflows GA  
Claude Tag — monitor a channel or data source, kick off tasks  
Automatic code + security review  
Agent sandboxing  
CLAUDE.md and Skills for standards — skills registry  
Tune auto mode classifier from team usage  
Token controls: model selection, advisors, LSPs, lazy Skills vs bloated root CLAUDE.md  
Guardrails: Sandboxing, encoded standards, cost monitoring, proactive routines scoped to well-defined streams (bug triage, dependency upgrades, migrations).  
  
How to reach Step 4: Scaled automation of domain use cases — code migration, fuzzing, feature-building, feedback remediation. Code with Claude Tokyo shipped managed agents, scheduling, and vaults as infrastructure for this step.  
  
For advisor + executor splits (Fable plans, Sonnet executes), see Fable advisor + Sonnet executor — a common Step 3 pattern before full autonomy.  
  
Step 4 — AI-native (1,000+ agents, intent steering)  
  
What it looks like: The loop is fully closed. Most agents are kicked off by Claude, not humans. Hundreds to thousands of agents run; you steer by intent and monitor by exception.  
  
Unlock: A quarter-long migration becomes a workflow you kick off and check on.  
  
Bottleneck: Identifying and automating work at scale while enforcing the right guardrails per work type — not one blanket policy.  
  
Products:  
  
Claude Agent SDK — programmatic build and schedule agents; see programmatic usage credits  
Claude Tag active in most Slack channels, auto-responding  
Cost controls for automation  
Model selection for automation (cheaper models for bulk, frontier for judgment)  
Guardrails: Per-workflow cost caps, exception-based monitoring, separation between automation lanes (migrations, triage) and human-gated lanes (production deploys, security-sensitive refactors).  
  
Cherny wrote Anthropic is pushing toward Step 4; he personally claimed Step 4 on July 17, 2026. Treat that as internal dogfooding signal, not a guarantee your team can copy day one without Step 2–3 harness investment.  
  
What Cherny emphasized on X (July 17)  
  
Beyond the table, Cherny's thread named concrete advance requirements:  
  
THEME CHERNY'S GUIDANCE  
Verification Give Claude ways to verify its own work end to end  
Permissions Auto mode for permissions; pre-approve safe commands  
Review defaults Automated code review + security review on by default  
Multi-agent UI Agent view in CLI, Desktop, iOS — manage multiple agents  
Background payoff Fixing and maintaining in the background; teams focus on building  
No universal path Every team different — break bottlenecks, don't just buy tokens  
When the published page had Safari scroll bugs, Cherny pointed to a Google Doc mirror of the same framework — worth bookmarking if the claude.ai page misbehaves.  
  
Mapping Cherny's steps to explainx.ai coverage  
  
STEP EXPLAINX.AI DEEP DIVES  
1 → 2 Loop engineering, Claude Code loops official guide, dynamic workflows  
2 Worktree / parallel patterns, Claude Code commands + /checkup  
2 → 3 Context / prompt / loop / harness stack, managed agents Tokyo  
3 Fable advisor patterns, Skills registry, MCP tool selection  
4 Claude Agent SDK credits, Claude Reflect usage dashboard  
Where is your team — honest self-assessment  
  
Cherny's ladder is descriptive, not a certification. Common misreads:  
  
MISREAD REALITY  
"We bought Enterprise so we're Step 3" Step 0–1 is about behavior, not SKU — one supervised session is still Step 1  
"We run 10 Cursor tabs so we're Step 2" Step 2 requires self-verification, auto mode, and automated review — not just parallel chats  
"We enabled /loop so we're Step 4" Proactive loops without trust + cost controls is Step 3 at best — often Step 2 with extra tokens  
"One 10× engineer means the org is advanced" Cherny's opening observation — individual heroics without guardrails widens internal inequality  
Run Cherny's question at Step 3+: would an engineer have done this task? If yes, automate. If no, keep a human gate.  
  
Free AI Skills Evaluation. Are you ready for the AI world?. Get your level and a personalized learning track — no signup required..  
LVL ?  
Are you ready for the AI world?  
  
Get your level and a personalized learning track — no signup required.  
  
CHECK MY LEVEL  
→  
Summary  
  
Boris Cherny's Steps of AI Adoption (July 16, 2026) names five maturity levels for Claude Code teams: Gated (0) → Assisted (~1) → Parallel (~10) → Supervised autonomy (~100) → AI-native (1,000+). Each step defines your role, the unlock, the bottleneck, Anthropic products, and guardrails to advance. Tokens alone do not move you forward — verification loops, auto mode, automated review, worktree isolation, routines, and cost monitoring do. Anthropic reports Step 3 org-wide; Cherny claims Step 4 personally. Map your team by behavior, not license tier.  
  
Related on explainx.ai  
  
Claude Code loops official guide — /goal, /loop, /schedule  
Loop engineering for coding agents  
Should developers stop reviewing AI-generated code?  
Claude Code dynamic workflows  
Code with Claude Tokyo — managed agents and scheduling  
Claude Code commands reference + /checkup  
Fable advisor + Sonnet executor setup  
Claude Reflect usage dashboard and AI fluency  
kache — programming as low-intelligence drudgery debate  
Agent skills complete guide  
Official sources: Steps of AI Adoption (Boris Cherny, Jul 16, 2026) · @bcherny X thread (Jul 17, 2026) · Claude Code docs  
  
**TL;DR — what each bar means**  

| PHASE | COLOR | TIME | WHAT AI ACTUALLY ACCELERATES |
| ----------------- | ------ | --------- | ----------------------------------------------------------------------------- |
| Idea | Green | ~5 min | Brainstorming, spec drafts, architecture sketches, prompt → scaffold |
| Working demo | Yellow | ~2 hours | Happy-path UI, CRUD, agent-driven file edits, local test green once |
| Final 10% | Red | ~6 months | Edge cases, security, perf, a11y, migrations, observability, legal/compliance |
| Abandoned project | Blue | ∞ | Demo shipped to X; red bar never funded; repo archived |
  
Ray ++[@ravikiran_dev7](https://x.com/ravikiran_dev7?ref=explainx)++ captured the Claude estimation joke in the same thread: Claude says "this project will probably take 3 months" — while the chart says the demo took two hours. Both can be true. Agents estimate production completion; builders celebrate demo completion.  
  
**Why the yellow bar collapsed but the red bar didn't**  
**What got faster (green + yellow)**  
Tools like ++[Claude Code](https://www.anthropic.com/claude-code?ref=explainx)++, Cursor, Codex, and Kimi K3-class models changed the first two bars:  
* Idea → runnable code no longer requires a sprint of manual scaffolding  
* In-IDE agents edit files, run tests, and iterate on errors without context-switching to Stack Overflow  
* Vision + UI models turn screenshots into components — the demo bar is literally what ++[nextjs.org/evals](https://www.explainx.ai/blog/kimi-k3-nextjs-evals-frontend-code-arena-july-2026)++ and Arena Frontend Code measure  
This is real. It is not hype. It is also misleading if you stop measuring after yellow.  
**What didn't get faster (red)**  
The final 10% is everything that does not show in a Loom:  

| RED-BAR WORK | WHY AGENTS STRUGGLE |
| ----------------------- | --------------------------------------------------------------------- |
| Edge cases | Long tail of user behavior — sparse in training data |
| Security | Threat modeling requires adversarial thinking, not pattern completion |
| Performance at scale | Demos run on happy paths; prod runs on p99 and noisy neighbors |
| Accessibility & i18n | Easy to forget in a 2-hour demo; expensive to fix later |
| Observability & on-call | Metrics, alerts, runbooks — invisible in a screen recording |
| Migration & rollback | Real users have existing data; demos use seed fixtures |
  
Kr$na's chart is the 2026 restatement of the 90% rule: the last mile was always disproportionately expensive. AI moved the demo milestone left on the timeline; it did not repeal Brooks's law for polish.  
  
**ThePrimeagen, Chollet, and the skill debate**  
The chart triggered agreement more than controversy — ThePrimeagen's "first principles" line landed because senior builders already lived this shape before LLMs. AI just made the gap between bars 2 and 3 visually absurd.  
The skill question is separate:  

| VIEW | WHO SAID IT | IMPLICATION |
| ---------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------- |
| AI amplifies experts | François Chollet | Stronger codegen rewards people who specify constraints and catch bad evidence |
| Interfaces matter more than typing | ThePrimeagen | Defining structs, APIs, and boundaries — acceptable to be the review bottleneck |
| Demo code doesn't scale | Mitchell Hashimoto vibe-coding thread | Prototypes that skip red-bar work demand painful rewrites |
  
explainx.ai covered this split in ++[should developers stop reviewing AI-generated code?](https://www.explainx.ai/blog/should-developers-stop-reviewing-ai-generated-code-2026)++. Kr$na's chart does not pick a side — it shows where calendar time goes if you treat yellow as done.  
Emil Kowalski (++[@emilkowalski](https://x.com/emilkowalski?ref=explainx)++, Linear, ++[animations.dev](https://animations.dev/?ref=explainx)++) sits in the design-polish camp the red bar describes: motion, micro-interactions, and feel are exactly the kind of work that does not compress to two hours because they require taste loops, not token loops.  
  
**Mapping the chart to Boris Cherny's adoption ladder**  
Cherny's ++[Steps of AI Adoption](https://www.explainx.ai/blog/boris-cherny-steps-ai-adoption-claude-code-july-2026)++ (published the same week) names why teams stall in the red bar:  

| CHERNY STEP | CHART BAR | BOTTLENECK |
| -------------------------- | ------------------------ | ---------------------------------------------------------------- |
| Step 1 Assisted | Yellow (supervised demo) | You read every edit — fast demo, slow trust |
| Step 2 Parallel | Yellow → early red | Self-verification (tests, lint, security scan) before you review |
| Step 3 Supervised autonomy | Red in background | Proactive maintenance — polish runs while you build |
| Step 4 AI-native | Red automated per domain | Migrations, triage, fuzzing — if guardrails exist |
  
Teams stuck at Step 1 get incredible yellow bars and brutal red bars — because every edge case still needs human eyes. Advancing to Step 2 means investing in the verification loop that shrinks red without abandoning to blue.  
See ++[loop engineering](https://www.explainx.ai/blog/loop-engineering-coding-agents-claude-code-guide-2026)++ and ++[Claude Code /goal, /loop, /schedule](https://www.explainx.ai/blog/claude-code-loops-official-guide-turn-goal-schedule-2026)++ for the harness layer between demo and production.  
  
**The infinity bar — why projects die after great demos**  
The blue ∞ segment is the chart's punchline. Common paths:  
1. Demo-as-marketing — thread goes viral; no budget for red bar  
2. Rewrite trap — yellow code is so demo-shaped that red costs more than greenfield  
3. Scope creep in red — "just one more edge case" without a ship date  
4. Burnout — yellow was exhilarating; red is ++[LLM prose and clanker fatigue](https://www.explainx.ai/blog/programmers-mental-health-ai-agents-meditation-2026)++  
5. Wrong owner — PM prototype mistaken for eng-ready (++[vibe coding for PMs](https://www.explainx.ai/blog/vibe-coding-for-product-managers-guide-2026)++ warns: don't productionize the prototype)  
Mitigation that actually works:  
* Define red-bar done before yellow — test matrix, SLO, threat model, launch checklist  
* Separate repos or branches for demo spikes vs production lineage  
* Time-box yellow — 2 hours is the chart's joke; make it a literal cap for spikes  
* Automate red entry — CI fails on missing tests; security review on by default (Cherny Step 2)  
* Kill blue early — if red estimate exceeds value, archive at yellow instead of limping to ∞  
  
**What Claude's "3 months" estimate actually means**  
When Claude (or any agent) says a project takes three months, it is often integrating:  
* Full red-bar scope (correct for production)  
* Unknown unknowns in your domain  
* Sequential human review bottlenecks  
When you finish in two hours, you built yellow. Both statements coexist. The failure mode is shipping yellow while believing you skipped red — the path to Hashimoto-style rewrites and the infinity bar.  
For enterprise teams, this is why ++[AI copy vs craft debates](https://www.explainx.ai/blog/ai-copying-creativity-shadcn-debate-july-2026)++ and ++[anti-slop design skills](https://www.explainx.ai/blog/nutlope-hallmark-anti-ai-slop-design-skill-july-2026)++ matter: demos default to generic; polish is differentiation.  
  
**Practical checklist — shrink red without lying to yourself**  

| BEFORE YOU POST THE DEMO           | BEFORE YOU CALL IT PRODUCTION        |
| ---------------------------------- | ------------------------------------ |
| Label it spike / POC in README     | CI green on your edge-case suite     |
| List 10 things that will break     | Security review or threat model doc  |
| Pick one user persona for yellow   | Observability: logs, metrics, alerts |
| Set red budget (days, not ∞)       | Rollback tested                      |
| Use Plan mode / advisor for intent | On-call owner named                  |
  
If red budget exceeds value → archive at yellow. That is healthier than the infinity bar.  
++[Free AI Skills Evaluation. Are you ready for the AI world?. Get your level and a personalized learning track — no signup required..](https://www.explainx.ai/ai-evaluation)++  
  
  
  
  
  
LVL ?  
Are you ready for the AI world?Get your level and a personalized learning track — no signup required.  
CHECK MY LEVEL  
→  
  
**Summary**  
Kr$na's July 16, 2026 chart names the 2026 software calendar: 5-minute idea, 2-hour working demo, 6-month final 10%, ∞ abandoned. AI coding agents genuinely compressed green and yellow — Claude Code, Cursor, and frontier models turn scaffolding into an afternoon. ThePrimeagen treated it as first principles; the 90% rule explains why red still dominates. Skill debates (Chollet, Hashimoto) are about who steers, not whether the shape is real. Avoid the blue bar by defining red-bar done early, time-boxing demos, and advancing to verification-heavy agent maturity — not by pretending yellow is ship.  
