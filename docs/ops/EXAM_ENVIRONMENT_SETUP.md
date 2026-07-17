# extraction-exam environment — REQUIRED settings checklist (founder)

The attended golden-set exam's secret boundary is GitHub's environment
configuration, not workflow code (a branch-modified workflow copy can
delete any in-file guard — evaluator r19/r22). The dispatch workflow
PROVES these settings via the API before touching the secret and dies if
any is missing, but the settings themselves live here, out of band:

Page: https://github.com/schubertsean-ui/onelive/settings/environments →
`extraction-exam`

1. **Deployment branches** → **Selected branches** → add the repository's
   DEFAULT branch only (currently `master`). (Not "protected branches"
   mode — it can include non-default branches.) This is the actual
   boundary: GitHub itself refuses the environment to any workflow run
   not on that branch, whatever its code says. The workflows check the
   default branch dynamically, so if the default branch is ever renamed,
   this list is the ONE thing to update to match — the dispatch run will
   fail closed with instructions until it does.
2. **Environment secrets** → `ANTHROPIC_API_KEY_EXAM` = the Anthropic API
   key (create a fresh key at https://console.anthropic.com/settings/keys
   if needed; same account, same spend cap). This name exists nowhere
   else — no other workflow can reference it.
3. Do NOT add the key as a repository-level secret, and do not reuse the
   repo-wide ANTHROPIC_API_KEY name here.

Verification: dispatch "Extraction Golden-Set Exam — attended run" from
the default branch; its first (secretless) step reports the policy proof
result and fails with instructions if anything above is missing.

## attended-review environment (added with PR #32 — evidence-bearing reviews)

Same mechanism, second box, for the OpenAI reviewer key used ONLY by
attended (dispatch-mode) reviews that attach exam evidence:

Page: https://github.com/schubertsean-ui/onelive/settings/environments →
`attended-review` (create with that exact name)

1. **Deployment branches** → **Selected branches** → add the repository's
   DEFAULT branch only (currently `master`) — same as extraction-exam.
2. **Environment secrets** → `OPENAI_API_KEY_ATTENDED` = the same OpenAI
   API key already used by CI (paste it only into that GitHub form). The
   distinct NAME is deliberate: if this environment is missing, the
   attended job gets an EMPTY key and fails loud — it can never silently
   fall back to the repo-level secret.
3. The repo-level `OPENAI_API_KEY` remains in use by the base-owned
   review job only (pull_request_target: the PR's workflow copy never
   runs, and no PR code executes in the job that holds the key — PR code
   runs exclusively in the secretless subject-checks job).

Verification: dispatch "Adversarial Review (non-Claude)" from the default
branch with an `exam_head_sha`; its first (secretless) step reports the
policy proof result and fails with instructions if anything is missing.
