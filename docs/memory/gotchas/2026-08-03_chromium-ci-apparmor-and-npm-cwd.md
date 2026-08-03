# Gotcha — headless Chromium on CI runners + npm's silent wrong-cwd install

**Retrieval tokens:** chromium, headless, screenshot, AppArmor, core dumped,
no-sandbox, dev-shm, visual regression, npm install, stray package.json

## 1. Chromium ABORTS on ubuntu-24 GitHub runners unless --no-sandbox

Symptom: `Aborted (core dumped)` from a plain `chromium --headless
--screenshot` step (proven: run 30840138414 on PR #152). Cause: ubuntu-24
images restrict unprivileged user namespaces via AppArmor, so Chromium's
sandbox cannot start; the runner's small `/dev/shm` separately crashes the
renderer on bigger pages. Fix used by `tools/visual_check.sh` +
`web/qa/audit.mjs`: always launch with `--no-sandbox
--disable-dev-shm-usage`. Safety reasoning (state it when reusing): only
acceptable because the browser is a single-use CI/sandbox machine rendering
OUR OWN localhost fixture pages with every external host resolver-blocked
(`--host-resolver-rules="MAP * 127.0.0.1, EXCLUDE localhost"`). Verified the
flags change ZERO pixels (0/329160 diff against sandboxed-capture baselines).

Related pin: the preinstalled sandbox browser is Chromium build 1194 =
**playwright 1.56.0** (found by mapping playwright-core tarballs'
browsers.json; 1.57→1200, 1.58→1208). Pixel baselines are bound to that
build — CI must install the same one, and a version bump must recapture
baselines in the same PR.

## 2. npm i in the wrong cwd invents a root package.json — silently

Symptom: `npm i -D x` reported success and updated "package.json", but the
web app couldn't resolve the package. npm had run at the REPO ROOT (shell cwd
had been reset), where no package.json existed — so npm CREATED
`/package.json` + `/node_modules` instead of erroring. Fix: delete the stray
files, reinstall inside `web/`. Rule: after any `npm i`, verify the intended
`node_modules/<pkg>/package.json` exists at the intended path before trusting
the install — and remember this harness resets the shell cwd between calls.
