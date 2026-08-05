"""The Eventbrite event-id allow-list must be MECHANICALLY bound to real
harvest evidence — never a self-attested claim.

Evaluator finding (PR #178 r2): the registry is the trust boundary for
`--kind event` imports, but a JSON file's own "founder approved" prose is
forgeable — an insider could append arbitrary ids and self-attest. Actor-based
founder authentication is structurally impossible while the repo has a single
shared push identity (R-079), so the strongest available authentication is
EVIDENCE binding, the same architecture as the arming smoke evidence:

  git side (always runs): the registry parses, every event id is numeric,
  and the harvest-run binding fields are present.

  API side (REQUIRED wherever ARMING_SMOKE_VERIFY=required — the same
  required-verification switch the trust-gate job already sets; one venue,
  one switch): the recorded harvest run exists, succeeded, ran
  provider-dryrun.yml; the recorded artifact belongs to it with the recorded
  digest; the artifact BYTES are downloaded, re-hashed against that digest,
  and every registry event id must appear in the harvest output inside it.
  An id that never came out of a real harvest run cannot enter the lane.

Additions to the registry therefore require a real harvest run (whose
artifact contains the new ids) + the mandatory adversarial review on the PR
that adds them. Founder curation remains recorded as honest provenance in
the file; it is deliberately NOT the load-bearing gate.
"""
import hashlib
import io
import json
import os
import pathlib
import urllib.request
import zipfile

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_REGISTRY = _ROOT / "sources" / "eventbrite_provenance.json"


def _load():
    return json.loads(_REGISTRY.read_text(encoding="utf-8"))


def test_registry_shape_and_numeric_ids():
    data = _load()
    ids = [e["event_id"] for e in data["event_ids"]]
    assert ids, "empty allow-list would silently disable the lane's purpose"
    assert all(i.isdigit() for i in ids), "non-numeric id in the allow-list"
    assert len(set(ids)) == len(ids), "duplicate ids in the allow-list"
    run = data["harvest_run"]
    for field in ("run_id", "artifact_id", "artifact_zip_sha256", "run_url"):
        assert run.get(field), f"harvest_run.{field} missing — the registry " \
                               "must bind to real harvest evidence"


def test_registry_ids_exist_in_the_authenticated_harvest_artifact():
    data = _load()
    run_binding = data["harvest_run"]
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    required = os.environ.get("ARMING_SMOKE_VERIFY") == "required"
    if not token:
        assert not required, (
            "ARMING_SMOKE_VERIFY=required but no GH_TOKEN/GITHUB_TOKEN — the "
            "harvest evidence CANNOT be authenticated; failing closed."
        )
        pytest.skip("no Actions API token here — authoritative venue is the "
                    "trust-gate required check (ARMING_SMOKE_VERIFY=required).")
    repo = os.environ.get("GITHUB_REPOSITORY", "schubertsean-ui/onelive")

    class _Redirected(Exception):
        def __init__(self, url):
            self.url = url

    class _StopRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise _Redirected(newurl)

    def _get(url, raw=False):
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        })
        if not raw:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        # Artifact downloads 302-redirect to a signed blob-storage URL that
        # REJECTS a forwarded GitHub Authorization header (401 on run
        # 30971391913) — catch the redirect and fetch the signed URL bare.
        opener = urllib.request.build_opener(_StopRedirect())
        try:
            with opener.open(req, timeout=60) as resp:
                return resp.read()
        except _Redirected as red:
            bare = urllib.request.Request(red.url)
            with urllib.request.urlopen(bare, timeout=60) as resp:
                return resp.read()

    try:
        run = _get(f"https://api.github.com/repos/{repo}/actions/runs/"
                   f"{run_binding['run_id']}")
    except Exception as exc:  # noqa: BLE001 — tolerated ONLY when not required
        assert not required, (
            f"ARMING_SMOKE_VERIFY=required but the Actions API is "
            f"unreachable ({type(exc).__name__}) — failing closed."
        )
        pytest.skip(f"Actions API unreachable here ({type(exc).__name__}) — "
                    "authoritative venue is the trust-gate required check.")
    assert run["conclusion"] == "success"
    assert run["path"] == ".github/workflows/provider-dryrun.yml"

    arts = _get(f"https://api.github.com/repos/{repo}/actions/runs/"
                f"{run_binding['run_id']}/artifacts")["artifacts"]
    match = [a for a in arts if str(a["id"]) == str(run_binding["artifact_id"])]
    assert match, f"recorded artifact {run_binding['artifact_id']} not on run"
    art = match[0]
    assert art["name"] == "eventbrite-harvest-candidates"
    digest = art.get("digest")
    if digest:
        assert digest == f"sha256:{run_binding['artifact_zip_sha256']}", digest

    blob = _get(art["archive_download_url"], raw=True)
    assert hashlib.sha256(blob).hexdigest() == run_binding["artifact_zip_sha256"], (
        "downloaded artifact bytes do not match the recorded digest"
    )
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        harvest = json.loads(zf.read("eventbrite-harvest.json").decode("utf-8"))
        resolved = json.loads(zf.read("eventbrite-resolved-orgs.json").decode("utf-8"))
    harvested_ids = {e["event_id"] for e in harvest["event_ids"]}
    registry_ids = {e["event_id"] for e in data["event_ids"]}
    rogue = registry_ids - harvested_ids
    assert not rogue, (
        f"registry event id(s) NOT present in the authenticated harvest "
        f"artifact: {sorted(rogue)} — an id that never came out of a real "
        "harvest run must not enter the import lane."
    )
    resolved_orgs = {o["org_id"] for o in resolved["organizers"]}
    registry_orgs = {o["org_id"] for o in data["organizers"]}
    assert registry_orgs <= resolved_orgs, (
        f"registry organizer(s) not in the resolve output: "
        f"{sorted(registry_orgs - resolved_orgs)}"
    )
