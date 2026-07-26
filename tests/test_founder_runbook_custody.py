"""Mechanical custody contract for docs/ops/FOUNDER_SETUP_STEPS.md.

WHY THIS EXISTS, stated as the failure it replaces. Across PR #73 the same
finding landed four times, and each time I fixed the lines the reviewer cited
and left the siblings:

  * r10 — a non-CSPRNG generator offered beside a safe one;
  * r19 — one of FOUR key-generation paths left below the 64-char floor;
  * r24 — the password-manager path still naming Apple Passwords while the
    iPhone path refused it, and a "send a screenshot to Claude" line sitting
    above the steps that display a bearer token;
  * r25 — BOTH credential ROTATION paths missing the clipboard-clear step that
    their own initial-store paths carry.

The pattern is not carelessness about any one rule; it is that a prose runbook
has no gate, so "I swept it" was always a claim about my attention rather than
a fact about the file. RECOVERY paths in particular kept being missed, because
they are written last and read least — which is exactly backwards, since a
rotation runs *after* something already went wrong.

So the sweep becomes mechanical. These tests read the runbook and assert
structural properties over EVERY matching block, so a new credential path — or
a new recovery path under an existing one — cannot ship without its boundary.
A test that fails is the point: it names the block and the missing step.

Scope, stated honestly: this checks that the required INSTRUCTIONS ARE PRESENT
in the right blocks. It cannot check that they are correct English or that a
founder follows them — a genuine boundary of any static check. It replaces
"I read the whole file" with "the file has these properties", which is strictly
more than prose review gave, and strictly less than a proof of safety.

A STATED LIMIT IS A TO-DO, NOT AN ALIBI (r28). This docstring used to carry a
second limit — "does not audit ordinary mint/store steps, only recovery paths"
— written at r25 as a design choice. It was a coverage gap, and r28 found the
leak inside it: §1c copies a publish-capable token, and no test could see it.
The lesson is about scope, not about that step. Across r25-r28 this suite was
right about the class every time and wrong about the SCOPE every time, because
each scope was drawn around the previous finding — recovery paths, then a
hand-listed set of screens, then an exemption that contained a token, then
credentials-defined-as-env-var-names. The asset is none of those. The asset is
ANY VALUE THAT CAN ACT AS THE FOUNDER, wherever the document produces, shows,
copies, stores or replaces one. New coverage goes there, and any limit named
here that is not an inherent boundary of static checking is an open defect
carrying a RECORD row, never a sentence that excuses itself.
"""
import pathlib
import re

_DOC = (pathlib.Path(__file__).resolve().parent.parent
        / "docs" / "ops" / "FOUNDER_SETUP_STEPS.md")
_TEXT = _DOC.read_text(encoding="utf-8")
_LINES = _TEXT.splitlines()

# The bearer/signing credentials this runbook mints. Anything added to this
# tuple is immediately held to every rule below — which is the intended way to
# extend the file: add the name here first and let the tests say what is owed.
#
# r28: this list said "the TWO credentials" and named only the two ENV VAR
# names, which silently excluded the SHORT-LIVED Meta token copied at §1c step
# 6. That token already carries instagram_content_publish — it can post from
# the moment it exists — so the enumeration was false and the suite could go
# green while a publish-capable bearer path had no boundary at all. A custody
# test whose own vocabulary omits a credential is worse than no test: it
# converts an open leak into a documented "custody contract".
_SECRETS = ("META_ACCESS_TOKEN", "ONELIVE_APPROVAL_KEY")

# Credential MINT/COPY points that are not named by an env var. Each must carry
# its own nondisclosure boundary at the point of copying, not deferred to a
# later step that exchanges or stores it.
# r29: this held ONE anchor, so a test named
# "every_mint_point_carries_its_boundary" could pass while every OTHER copy or
# store point in the file lost its boundary. A one-anchor allowlist is not an
# inventory. Enumerated from the runbook by grepping its own copy/paste/store
# instructions, so adding a credential step to the document without its boundary
# now reds here.
#
# `needs` says WHICH boundary each point owes, because they are not the same
# obligation: a COPY point owes the nondisclosure rules (chat/email prohibition
# + a burn path), while a STORE point owes the clipboard clear. Demanding both
# everywhere would be noise, and a noisy gate gets weakened.
_MINT_POINTS = (
    ("short-lived Meta token (§1c/6, copy)",
     "Copy the token that appears in the", "disclose"),
    ("long-lived META_ACCESS_TOKEN (§1d/4, copy)",
     "Copy the new token.", "disclose"),
    ("META_ACCESS_TOKEN initial store (§1f/3)",
     "Secret: paste the long-lived token", "clipboard"),
    ("META_ACCESS_TOKEN rotation store (§1d recovery/d)",
     "Paste the new token and click", "clipboard"),
    ("ONELIVE_APPROVAL_KEY initial store (§2/5)",
     "Value: paste the generated key", "clipboard"),
    ("ONELIVE_APPROVAL_KEY rotation store (§2/9d)",
     "Paste the new value, keep", "clipboard"),
)

# A step that puts a secret somewhere durable: the moment after which a stray
# copy is the founder's exposure rather than a transient.
#
# NEGATION-AWARE, and this was found by RUNNING the test rather than reasoning
# about it: the first version fired on "Do NOT paste the key into a chat" — a
# PROHIBITION, i.e. one of the boundaries this file exists to state. A custody
# gate that reds on the safety rules themselves is noise, and a noisy gate is
# one that gets weakened, so prohibitions are excluded explicitly.
_STORE_STEP = re.compile(
    r"(?:paste|update|save)\b[^\n]{0,120}"
    r"(?:secret|token|key|value)",
    re.IGNORECASE)
_PROHIBITION = re.compile(
    r"\b(?:do\s+not|don't|never|refus\w+|must\s+not)\b", re.IGNORECASE)


def _is_store_instruction(text: str) -> bool:
    """True only for an imperative to STORE a secret — never for a rule about
    where it may not go.

    THIRD correction found by running it, and the bug is instructive: an earlier
    version treated a NEWLINE as a clause boundary, so the wrapped prohibition
    "Do NOT\n    paste the key" read as a bare "paste the key" and the rule
    became a violation of itself. In wrapped markdown a line break is cosmetic;
    only sentence punctuation ends a clause. Normalise the wrapping FIRST.
    """
    flat = " ".join(text.split())
    m = _STORE_STEP.search(flat)
    if not m:
        return False
    # Clause = back to the nearest sentence boundary, newlines already gone,
    # and FORWARD only to the next one.
    #
    # FIFTH correction, and mutation is the only reason it was found: a fixed
    # 40-character lookahead reached into the FOLLOWING bullet, so the real
    # store step "Paste the new token and click Update secret" was dismissed
    # because the next line happened to read "The two IDs do NOT change". The
    # gate then passed with the r25 fix deleted — the same fail-open shape as
    # the section-wide search, in a different disguise. A negation only counts
    # when it governs THIS clause.
    bounds = [flat.rfind(c, 0, m.start()) for c in (".", ";", ":")]
    fwd = [i for i in (flat.find(c, m.end()) for c in (".", ";")) if i != -1]
    clause = flat[max(bounds) + 1:(min(fwd) if fwd else len(flat))]
    return not _PROHIBITION.search(clause)

_CLIPBOARD_CLEAR = re.compile(
    r"clear it from your clipboard|clear your clipboard|"
    r"overwrite it|delete (?:that|any temporary) copy",
    re.IGNORECASE)


def _blocks() -> list[tuple[str, int, int]]:
    """Split the doc into numbered top-level sections (## / ###) so a finding
    can name WHERE, not just THAT. Returns (heading, start, end) line spans."""
    heads = [i for i, l in enumerate(_LINES) if l.startswith("## ")]
    out = []
    for n, start in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(_LINES)
        out.append((_LINES[start].strip("# ").strip(), start, end))
    return out


def _sections_mentioning(secret: str) -> list[tuple[str, int, int]]:
    return [b for b in _blocks()
            if secret in "\n".join(_LINES[b[1]:b[2]])]


def test_every_secret_this_runbook_mints_is_actually_covered():
    """Guard against the tests below passing vacuously: each named secret must
    really appear in the document, or the whole file's coverage is a fiction."""
    for secret in _SECRETS:
        assert secret in _TEXT, (
            f"{secret} is listed in _SECRETS but absent from the runbook — "
            "either the doc dropped it (and these tests silently stopped "
            "checking anything) or the name is stale")


def test_every_credential_recovery_block_clears_the_clipboard():
    """r25 blocker, expressed as the property that actually failed twice.

    SCOPE CHOSEN DELIBERATELY, after mutation testing rejected a broader
    version. The first attempt classified every paste/update/save of a secret
    anywhere in the file, and it went wrong in both directions: searching to the
    end of the SECTION let a clear 150 lines away satisfy a rotation path (it
    passed with the exact r25 fix deleted — a gate that green-lights the blocker
    it cites), and tightening the window then fired on legitimate non-store
    pastes, like pasting a token into Graph Explorer to look up the two PUBLIC
    ids. Four corrections in, the lesson was that "is this paste a durable
    store?" is not reliably decidable from prose.

    So this checks the narrow thing that broke, and states its limit plainly:
    every RECOVERY / ROTATION block for a secret must contain a
    clipboard-clear instruction. Recovery blocks are exactly where both r25
    misses were, and they are unambiguously identifiable by their own headings.
    Mutation-verified below against the two real r25 deletions.

    r29: this docstring used to end "What it does NOT do: audit ordinary store
    steps. That is left to review." That sentence survived the r28 paragraph
    which declared exactly such sentences to be defect reports rather than
    alibis — I wrote the rule and left the alibi two functions below it. Ordinary
    store steps are now audited by
    test_every_mint_point_carries_its_boundary_at_the_point_of_copying over a
    complete inventory, so the exemption is gone rather than restated.
    """
    # A block that runs AFTER something went wrong: expiry, leak, burn, rotate.
    recovery_head = re.compile(
        r"(?:if it ever leaks|when it expires|if it leaks|treat it as burned"
        r"|recovery:|rotate it|rotated\b)", re.IGNORECASE)
    missing = []
    for secret in _SECRETS:
        for heading, start, end in _sections_mentioning(secret):
            body = _LINES[start:end]
            heads = [i for i, l in enumerate(body)
                     if re.match(r"^\d+\.\s", l) or re.match(r"^\*\*", l)]
            for n, h in enumerate(heads):
                e = heads[n + 1] if n + 1 < len(heads) else len(body)
                block = "\n".join(body[h:e])
                if not recovery_head.search(block):
                    continue
                # A recovery block that only CROSS-REFERENCES another path, or
                # whose only "paste" is a PROHIBITION ("Do NOT paste it into a
                # chat"), owes nothing here — the negation-aware helper is
                # exactly the discrimination this needs. Without it the block
                # stating the custody RULES was flagged for violating them.
                if not _is_store_instruction(block):
                    continue
                if not _CLIPBOARD_CLEAR.search(block):
                    missing.append(
                        f"§{heading} line {start + h + 1}: "
                        f"{body[h].strip()[:90]!r}")
    assert not missing, (
        "these credential RECOVERY / ROTATION blocks paste a replacement secret "
        "with no clipboard-clear or delete-temporary-copy instruction inside the "
        "block — recovery runs after something already went wrong, so it is the "
        "path where a stray copy is most likely and least noticed:\n  "
        + "\n  ".join(missing))


def test_no_generation_path_routes_a_secret_through_the_agent():
    """r24 blocker, generalised: the runbook must never tell the founder to
    obtain, relay, or transmit a secret via Claude/chat. Checked as an absence
    over the whole document, because ONE such sentence anywhere defeats every
    other boundary in the file."""
    # Scoped to TRANSMITTING OR OBTAINING THE VALUE. Found by running it: the
    # first version fired on `Tell Claude "token rotated"` — a status
    # NOTIFICATION whose own line goes on to forbid pasting the value. Telling
    # the agent that a rotation happened is the opposite of leaking it, so the
    # pattern now requires an object that is the credential itself, and skips
    # any line carrying a prohibition.
    forbidden = re.compile(
        r"(?:send|give|show|paste|relay)\s+(?:me\s+|it\s+|the\s+\w+\s+)?"
        r"(?:to\s+)?claude"
        r"|claude[^\n]{0,60}(?:will\s+|can\s+)?generate[^\n]{0,40}"
        r"(?:token|key|secret)"
        r"|ask\s+claude[^\n]{0,40}for\s+(?:a\s+)?(?:token|key|secret|value)",
        re.IGNORECASE)
    hits = [f"line {i + 1}: {l.strip()[:100]!r}"
            for i, l in enumerate(_LINES)
            if forbidden.search(l) and not _PROHIBITION.search(l)]
    assert not hits, (
        "the runbook appears to route a credential through the agent/chat "
        "path it forbids elsewhere:\n  " + "\n  ".join(hits))


def test_every_screenshot_instruction_carries_a_redaction_boundary():
    """r24 blocker, generalised. Any instruction to send an image must, in the
    same paragraph, tell the founder to crop and to check what is inside the
    crop — because the screens in this file display bearer tokens."""
    missing = []
    for i, line in enumerate(_LINES):
        if not re.search(r"screenshot|screen ?grab", line, re.IGNORECASE):
            continue
        # Paragraph = until the next blank line, in both directions.
        s = i
        while s > 0 and _LINES[s - 1].strip():
            s -= 1
        e = i
        while e < len(_LINES) - 1 and _LINES[e + 1].strip():
            e += 1
        para = "\n".join(_LINES[s:e + 1])
        if not (re.search(r"crop", para, re.IGNORECASE)
                and re.search(r"no token|confirm no|redact|check what is",
                              para, re.IGNORECASE)):
            missing.append(f"line {i + 1}: {line.strip()[:100]!r}")
    assert not missing, (
        "these screenshot instructions lack a crop-and-verify boundary in the "
        "same paragraph:\n  " + "\n  ".join(missing))


def test_key_generation_paths_never_offer_a_tool_the_document_itself_refuses():
    """r24 blocker, generalised: if the document says a named generator must NOT
    be used for a key, that generator must not also appear in an OFFER of
    acceptable generators. The r24 instance was Apple Passwords — refused on the
    iPhone path, offered eight lines earlier in the password-manager list.

    SENTENCE-SCOPED, and mutation is why. A first version asked whether a
    refusal appeared within two lines of the mention; re-adding Apple Passwords
    to the acceptable list then PASSED, because the refusal sitting just below
    it satisfied the window. Proximity is not context: an offer and a refusal
    can be neighbours and still contradict. The unit is the sentence that makes
    the claim.
    """
    tools = ("Apple Passwords", "Get-Random", "1Password", "Bitwarden")
    flat = " ".join(_TEXT.split())
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    refusal = re.compile(
        r"do NOT use|NOT acceptable|must not be used|Do NOT substitute|"
        r"cannot (?:satisfy|meet)|is not acceptable", re.IGNORECASE)
    # An OFFER: this sentence presents the tool as something to use.
    offer = re.compile(
        r"\buse (?:its|the|your)\b|generator\b|— ?[A-Z0-9]|open (?:its|the)\b",
        re.IGNORECASE)

    refused_tools = {tool for tool in tools
                     for s in sentences
                     if tool.lower() in s.lower() and refusal.search(s)}
    offenders = []
    for tool in sorted(refused_tools):
        for s in sentences:
            if tool.lower() not in s.lower():
                continue
            if refusal.search(s):
                continue
            if offer.search(s):
                offenders.append(f"{tool}: {s.strip()[:120]!r}")
    assert not offenders, (
        "the document refuses these generators for a key in one sentence and "
        "OFFERS them in another — a contradiction in a signing-key runbook is "
        "how a below-floor key gets minted, and a refusal printed nearby does "
        "not cancel an offer:\n  " + "\n  ".join(offenders))


def test_no_screen_declared_safe_contains_a_secret_bearing_step():
    """r27 blocker, and it is the invariant whose ABSENCE let my own r26 fix
    ship a hole. The r26 enumeration declared §1e "safe to send" on the grounds
    that its two IDs are public — but §1e step 1 instructs the founder to paste
    the long-lived token into the Access Token box, so the SCREEN shows a bearer
    credential even though its OUTPUT is public. A safe-screen exception that
    contains a secret is worse than no exception: it is an instruction to leak.

    The r25/r26 tests could not catch it, and that is the lesson. They checked
    that screenshot paragraphs mention crop-and-verify — a property of the
    WARNING. Nothing checked the property of the EXEMPTION. Every allow-list in
    a custody document needs an invariant that its members are actually safe,
    or the allow-list is the attack surface.

    So: no section named as safe/exempt may contain a step that displays or
    pastes a secret. Mutation-verified by re-adding the r26 wording.
    """
    flat = " ".join(_TEXT.split())
    # Sentences that EXEMPT a screen or section from the image boundary.
    exemption = re.compile(
        r"[^.]*\b(?:safe to (?:send|screenshot|share)|screens? (?:are|is) safe"
        r"|are NOT secrets[^.]{0,80}safe)\b[^.]*\.", re.IGNORECASE)
    # Section labels a sentence can name: "1e", "§2", "step 1f".
    label = re.compile(r"(?:§\s*\d+|\b1[a-f]\b|\bstep\s+\d+[a-f]?\b)")

    offenders = []
    for sentence in exemption.findall(flat):
        # A sentence can MENTION safety while REFUSING it — "the screen is not
        # safe even though its output is", "There is no safe section in this
        # file". Those are the fix, not the hole. Caught by running it: the
        # first version flagged the very sentence that closes this gap.
        if (_PROHIBITION.search(sentence)
                or re.search(r"\bnot safe\b|\bno\b\s+\"?safe", sentence,
                             re.IGNORECASE)):
            continue
        for named in set(label.findall(sentence)):
            key = named.replace("§", "").replace("step", "").strip()
            # Does the named section contain a secret on screen?
            sec = [b for b in _blocks()
                   if key in b[0] or any(key in l for l in _LINES[b[1]:b[2]]
                                         if l.startswith("### "))]
            for _, s, e in sec:
                body = "\n".join(_LINES[s:e])
                if _is_store_instruction(body) or re.search(
                        r"copy the token|Access Token\*\* box|Secret\*\* box",
                        body, re.IGNORECASE):
                    offenders.append(
                        f"{named} is exempted by {sentence.strip()[:90]!r} but "
                        "its section displays or pastes a secret")
    assert not offenders, (
        "a screen declared SAFE contains a secret-bearing step — an allow-list "
        "in a custody document must have every member verified, or the "
        "allow-list is the leak:\n  " + "\n  ".join(sorted(set(offenders))))


def test_every_mint_point_carries_its_boundary_at_the_point_of_copying():
    """r28 blocker, and the gap was in this file's own vocabulary.

    §1c step 6 copies the SHORT-LIVED Meta token. It already carries
    `instagram_content_publish`, so it can post from the moment it exists — but
    the full "do not paste into chat/email/repo" boundary lived only at §1d,
    the LONG-LIVED token. There was a real window with a publish-capable bearer
    credential and no handling rules, and my r25 scoping decision is why no test
    could see it: I wrote that this suite deliberately does not audit ordinary
    mint/store steps, only recovery paths, because recovery is where r25's
    finding was. For a custody document that is the wrong line to draw — the
    FIRST copy of a credential is a custody path too.

    A boundary is "at the point of copying" if the copy step's own block states
    the chat/email prohibition. Deferring it to a later step does not count:
    the founder acts on the step in front of them.
    """
    flat_lines = _TEXT.splitlines()
    missing = []
    for name, anchor, needs in _MINT_POINTS:
        idx = [i for i, l in enumerate(flat_lines) if anchor in l]
        assert idx, (
            f"the {name} mint point anchored on {anchor!r} is gone from the "
            "runbook — either the step moved (update _MINT_POINTS) or the "
            "coverage this test claims is a fiction")
        for i in idx:
            # Block = this numbered step and everything under it, to the next
            # top-level step or heading.
            e = next((j for j in range(i + 1, len(flat_lines))
                      if re.match(r"^(?:\d+\.\s|#{2,}\s)", flat_lines[j])),
                     len(flat_lines))
            block = " ".join("\n".join(flat_lines[i:e]).split())
            if needs == "disclose":
                has_chat = re.search(
                    r"do NOT paste it into a chat|not paste[^.]{0,40}chat",
                    block, re.IGNORECASE)
                has_burn = re.search(
                    r"treat it as burned|invalidate all access tokens",
                    block, re.IGNORECASE)
                if not (has_chat and has_burn):
                    missing.append(
                        f"{name} (line {i + 1}) — chat-prohibition: "
                        f"{bool(has_chat)}, burn-path: {bool(has_burn)}")
            else:
                # A STORE point owes the clipboard clear, and its window is the
                # enclosing ### subsection rather than the single step. That is
                # a deliberate distinction from the RECOVERY test above, not a
                # convenience: an initial-store sequence is worked top-to-bottom
                # in one sitting, so a clear four steps down is genuinely
                # reached; a recovery block is entered COLD, months later, out
                # of order, which is why r25 scopes that one to the block. Same
                # obligation, different reachability.
                # Bounded by ANY heading level, not just "###". Caught by
                # mutation: keying `sub_end` on "###" alone let §1f — the last
                # subsection of §1 — run on into §2 and borrow ITS clipboard
                # clear, so deleting 1f's own clear still passed. Third time a
                # too-wide window in this file produced a fail-open, and the
                # pattern is always the same: a scope defined by what comes
                # NEXT must name every kind of boundary that can come next.
                def _is_head(line: str) -> bool:
                    return line.startswith("#")

                sub_start = max((j for j in range(i, -1, -1)
                                 if _is_head(flat_lines[j])), default=0)
                sub_end = next((j for j in range(i + 1, len(flat_lines))
                                if _is_head(flat_lines[j])), len(flat_lines))
                block = " ".join("\n".join(
                    flat_lines[sub_start:sub_end]).split())
                if not _CLIPBOARD_CLEAR.search(block):
                    missing.append(
                        f"{name} (line {i + 1}) — no clipboard-clear / "
                        "delete-temporary-copy instruction in this block")
    assert not missing, (
        "these credential MINT points copy a bearer credential without stating "
        "its nondisclosure boundary in the same step — a boundary deferred to a "
        "later step does not protect the window before that step runs:\n  "
        + "\n  ".join(missing))
