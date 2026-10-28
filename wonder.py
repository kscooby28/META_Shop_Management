"""Muse Wonder router: hard cases get a visible second opinion.

Wonder Standard is the second opinion, never the first. The router
escalates only hard cases: low-confidence verdicts or plans, or anything
the shop flags hard. The opinion renders as a distinct card beside the
primary verdict or plan and never overwrites it; the owner sees both and
decides. Wonder Standard ONLY: Wonder Full is not on the pay-as-you-go
API and is not covered by hackathon credits, so it is never an option
here (WONDER_VARIANT is pinned and tested).

Isolated adapter with its own transport and key loading, following the
meta_client pattern. WONDER_LIVE stays False until the owner confirms
the Meta API key rotation; while False every escalation serves the demo
cache and never touches the network. The live model id and endpoint path
come from the local environment (MUSE_WONDER_MODEL, MUSE_WONDER_PATH)
and are never guessed: live refuses when either is unset.
"""

import json
import os
import urllib.error
import urllib.request

from meta_client import MetaAPIError

# Live second opinions stay OFF until the owner confirms the Meta API key
# rotation. While False, every escalation serves a demo-cache opinion and
# never calls the live API. Flipping this flag later changes the data
# source only; the interface does not change.
WONDER_LIVE = False
WONDER_VARIANT = "standard"
TIMEOUT_SECONDS = 30
KINDS = ("yard", "bay")


def _live_settings():
    dotenv = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                  "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key.strip() and value.strip():
                    dotenv[key.strip()] = value.strip().strip("'").strip('"')
    except OSError:
        pass
    base = (
        os.environ.get("META_API_BASE") or dotenv.get("META_API_BASE")
        or "https://api.meta.ai/v1"
    ).rstrip("/")
    return {
        "api_base": base,
        "model": os.environ.get("MUSE_WONDER_MODEL") or dotenv.get("MUSE_WONDER_MODEL") or "",
        "path": os.environ.get("MUSE_WONDER_PATH") or dotenv.get("MUSE_WONDER_PATH") or "",
    }


def _api_key():
    values = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                  "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip("'").strip('"')
    except OSError:
        pass
    key = (
        os.environ.get("META_API_KEY") or values.get("META_API_KEY")
        or os.environ.get("MODEL_API_KEY") or values.get("MODEL_API_KEY") or ""
    ).strip()
    if not key:
        raise MetaAPIError("no API key in local .env or environment", kind="auth")
    return key


WONDER_PROMPT = """You are a second-opinion reviewer for a shop copilot, not the
primary grader. Given one verdict or test plan plus its visible inputs as
JSON, reply with JSON only: {"agrees": true|false|"partial", "title": ...,
"body": ..., "watch": ...}. Judge only the evidence provided: state whether
you agree, say what would change your mind in "watch", and never invent
part numbers, prices, torque values, or labor times. Plain words."""


def request_opinion(evidence):
    """Ask Wonder Standard for a second opinion. Live only.

    Raises MetaAPIError without touching the network unless the live flag
    is on, evidence is present, and a model id and path are configured.
    """
    if WONDER_VARIANT != "standard":
        raise MetaAPIError("only Wonder Standard is allowed here", kind="unreachable")
    if not WONDER_LIVE:
        raise MetaAPIError("wonder live is off until the key rotation", kind="unreachable")
    if not evidence:
        raise MetaAPIError("no evidence to review", kind="bad_response")
    cfg = _live_settings()
    if not cfg["model"] or not cfg["path"]:
        raise MetaAPIError(
            "wonder live model/path unconfirmed; set MUSE_WONDER_MODEL and MUSE_WONDER_PATH",
            kind="unreachable",
        )
    body = json.dumps({
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": WONDER_PROMPT},
            {"role": "user", "content": json.dumps(evidence)},
        ],
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    request = urllib.request.Request(
        cfg["api_base"] + cfg["path"],
        data=body,
        headers={
            "Authorization": "Bearer " + _api_key(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise MetaAPIError("API key rejected (%s)" % exc.code, kind="auth")
        raise MetaAPIError("wonder API error %s" % exc.code, kind="unreachable")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise MetaAPIError("wonder API unreachable: %s" % exc, kind="unreachable")
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        assert isinstance(parsed.get("body"), str) and parsed.get("agrees") in (True, False, "partial")
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        raise MetaAPIError("wonder returned an unusable shape: %s" % exc, kind="bad_response")
    parsed.setdefault("title", "Second opinion")
    parsed.setdefault("watch", "")
    parsed["source"] = "wonder-live"
    return parsed


def assess_yard(verdict):
    """Visible trigger inputs for one yard verdict. Pure."""
    inputs = (verdict or {}).get("inputs", {})
    shown = {
        "grade": (verdict or {}).get("verdict", "?"),
        "price_known": bool(inputs.get("price_known")),
        "demand_sourced": bool(inputs.get("demand_source")),
        "intact": inputs.get("intact", "unknown"),
        "frames_seen": inputs.get("frames_seen", 0),
    }
    triggers = []
    if not shown["price_known"]:
        triggers.append("no reliable price")
    if not shown["demand_sourced"]:
        triggers.append("demand unsourced")
    if shown["intact"] == "unknown":
        triggers.append("condition unclear in photo")
    if shown["grade"] == "B":
        triggers.append("borderline grade (B)")
    return {"inputs": shown, "triggers": triggers}


def assess_bay(plan):
    """Visible trigger inputs for one bay plan. Pure."""
    plan = plan or {}
    results = plan.get("results", {})
    tests = plan.get("tests", [])
    suspected = plan.get("suspected", [])
    eliminated = plan.get("eliminated", [])
    open_gates = [
        t["title"] for t in tests
        if t.get("final_gate") and t.get("id") not in results
    ]
    shown = {
        "tests": len(tests),
        "recorded": len(results),
        "suspected": list(suspected),
        "eliminated": len(eliminated),
        "open_final_gates": open_gates,
    }
    triggers = []
    if len(suspected) >= 2:
        triggers.append("suspects split %d ways" % len(suspected))
    elif len(suspected) == 1 and len(eliminated) >= 1:
        triggers.append("one suspect standing, %d cause(s) ruled out" % len(eliminated))
    if open_gates:
        triggers.append("final gate still open: %s" % open_gates[0])
    if tests and not results:
        triggers.append("no results recorded yet")
    return {"inputs": shown, "triggers": triggers}


def demo_opinion(kind, ref, root):
    """Demo second opinion for a verdict or plan ref. Offline."""
    samples = {}
    try:
        with open(os.path.join(root, "demo_cache", "wonder.demo.json"),
                  "r", encoding="utf-8") as fh:
            samples = json.load(fh).get("samples", {})
    except (OSError, ValueError):
        pass
    found = samples.get("%s:%s" % (kind, ref)) or samples.get("%s:default" % kind) or {}
    return {
        "title": found.get("title", "Second opinion"),
        "body": found.get("body", ""),
        "agrees": found.get("agrees", "partial"),
        "watch": found.get("watch", ""),
        "source": "demo-cache: wonder sample",
    }


def escalate(kind, evidence, ref, root, hard=False):
    """Router entry: assess, then serve an opinion only for hard cases.

    Returns {assessment, escalated, opinion|null, mode}. Straight cases
    get no opinion; hard-flagged or triggered cases get the demo sample
    while the live flag is off, else a live attempt with demo fallback.
    """
    if kind == "yard":
        assessment = assess_yard(evidence)
    elif kind == "bay":
        assessment = assess_bay(evidence)
    else:
        raise MetaAPIError("kind must be yard or bay", kind="bad_response")
    if hard:
        assessment["triggers"].append("flagged hard by the shop")
    if not assessment["triggers"]:
        return {"assessment": assessment, "escalated": False,
                "opinion": None, "mode": "router"}
    if not WONDER_LIVE:
        return {"assessment": assessment, "escalated": True,
                "opinion": demo_opinion(kind, ref, root), "mode": "demo-cache"}
    try:
        opinion = request_opinion({"kind": kind, "ref": ref, "evidence": evidence,
                                   "triggers": assessment["triggers"]})
    except MetaAPIError:
        return {"assessment": assessment, "escalated": True,
                "opinion": demo_opinion(kind, ref, root), "mode": "demo-cache"}
    opinion["triggers"] = assessment["triggers"]
    return {"assessment": assessment, "escalated": True,
            "opinion": opinion, "mode": "live"}
